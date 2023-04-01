import os
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Dict, Optional

import git
from git import Repo
from matplotlib import pyplot as plt
from matplotlib.dates import date2num, DateFormatter, drange

from configuration import Configuration
from history_analyzer import AnalysisResult, calculate_percentage, CommitRange
from lib import FileGroup, Contributor, get_contributors, set_repo, compute_file_ownership, find_contributor, \
    stats_for_contributor, get_flagged_files_by_contributor, ContributionDistribution, Percentage, FlaggedFiles
from remote_repository_weight_model import RemoteRepositoryWeightModel
from repository_hooks import parse_project, Issue
from semantic_analysis import LangElement
from semantic_weight_model import SemanticWeightModel

from pathlib import Path
from collections import defaultdict

from uni_chars import *


def build_tree(triples):
    tree = {}
    for triple in triples:
        current = tree
        for part in triple[0].parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[triple[2]] = current.get(triple[2], 0) + triple[1]
    return tree


def calculate_ownership(tree, ownership_cache=None):
    if ownership_cache is None:
        ownership_cache = {}
    if all(isinstance(value, float) for value in tree.values()):
        return tree
    ownership = defaultdict(float)
    count = 0
    for value in tree.values():
        if isinstance(value, dict):
            sub_ownership = calculate_ownership(value, ownership_cache)
            for owner, value in sub_ownership.items():
                ownership[owner] += value
            count += 1
    for owner in ownership:
        ownership[owner] /= count
    ownership_cache[id(tree)] = ownership
    return ownership


def get_owner(ownership: Dict[Contributor, List[ContributionDistribution]], file: Path) -> Optional[Contributor]:
    for k, v in ownership.items():
        if file in map(lambda x: x.file, v):
            return k
    return None


def print_tree(tree, level=0, prefix='', ownership_cache=None):
    if ownership_cache is None:
        ownership_cache = {}
    for i, (name, value) in enumerate(tree.items()):
        if i == len(tree) - 1:
            connector = '└── '
            new_prefix = prefix + '    '
        else:
            connector = '├── '
            new_prefix = prefix + '│   '
        if isinstance(value, dict):
            if all(isinstance(v, float) for v in value.values()):
                owners_str = ', '.join([f'{owner}: {value * 100:.0f}%' for owner, value in value.items()])
                print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
            else:
                sub_ownerships = [calculate_ownership(v, ownership_cache) for v in value.values() if
                                  isinstance(v, dict)]
                if len(sub_ownerships) > 0 \
                        and all(sub_ownerships[0] == sub_ownership for sub_ownership in sub_ownerships):
                    print(f'{prefix}{connector}{name}')
                else:
                    owners_str = ', '.join([f'{owner}: {value * 100:.0f}%' for owner, value in
                                            calculate_ownership(value, ownership_cache).items()])
                    print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
                print_tree(value, level + 1, new_prefix, ownership_cache)


def plot_commits(commits: List[str], contributors: List[Contributor], repo: Repo,
                  force_x_axis_labels=False) -> None:
    commit_data = defaultdict(list)
    min_date = datetime.max.replace(tzinfo=timezone.utc)
    max_date = datetime.min.replace(tzinfo=timezone.utc)

    for commit in commits:
        commit_obj = repo.commit(commit)
        author = commit_obj.author.name
        for contributor in contributors:
            if author in contributor.aliases or author == contributor.name or author == contributor.email:
                committed_date = commit_obj.committed_datetime
                commit_data[contributor.name].append(date2num(committed_date))
                min_date = min(min_date, committed_date)
                max_date = max(max_date, committed_date)
                break

    plt.figure(figsize=(12, 6))

    for name, dates in commit_data.items():
        plt.plot_date(dates, range(len(dates)), label=name)
    plt.legend()
    plt.xticks(rotation=45)


    delta = timedelta(days=1)
    dates = drange(min_date, max_date, delta)

    if len(dates) <= 30 or force_x_axis_labels:
        plt.gca().xaxis.set_major_formatter(DateFormatter('%b %d'))
        plt.gca().xaxis.set_tick_params(which='both', labelbottom=True)
        plt.xticks(dates)
    else:
        print(f"{INFO} Skipping x-axis labels for all {len(dates)} dates to avoid cluttering the x-axis.")
        print(f" - Set force_x_axis_labels to True to override this behavior.")

    plt.show()


def separator() -> None:
    print()
    print("============================================")
    print()


def header(text: str) -> None:
    print(text)
    print()


def display_contributor_info(commit_range: CommitRange, config: Configuration) -> List[Contributor]:
    contributors = get_contributors(range=commit_range, explicit_rules=config.contributor_map)
    header(f"{CONTRIBUTOR} Contributors:")

    for contrib in contributors:
        print(contrib)

    return contributors


def commit_info(commit_range: CommitRange, repo: Repo, contributors: List[Contributor]) -> Dict[Contributor, int]:
    header(f"{COMMIT} Total commits: {len(commit_range.compute_path())}")

    commit_distribution: Dict[Contributor, int] = defaultdict(lambda: 0)

    for commit in commit_range:
        author = repo.commit(commit).author.name
        if author is None:
            continue
        contributor = find_contributor(contributors, author)
        if contributor is None:
            print(f'{INFO} Autor {author} not found in contributors. Skipping commit.')
            continue
        commit_distribution[contributor] += 1
        print(f'Commit: {commit} by {contributor.name}')

    print()
    header(f"{COMMIT} Commits per contributor:")

    for contrib, count in commit_distribution.items():
        print(f"{count} commits by: {CONTRIBUTOR} {contrib}")

    for contrib in contributors:
        insertion, deletion = stats_for_contributor(contrib, commit_range)
        print(f"{CONTRIBUTOR} {contrib.name}: inserted '{insertion}' lines and deleted '{deletion}' lines.")

    return commit_distribution


def percentage_info(syntax: AnalysisResult, contributors: List[Contributor], config: Configuration) \
        -> Tuple[Percentage, Dict[Contributor, List[ContributionDistribution]]]:
    header(f'{PERCENTAGE} Percentage of tracked files:')

    percentage = calculate_percentage(syntax)

    for c, p in percentage.global_contribution.items():
        print(f'\t{c}: {p:.2%}')

    ownership = compute_file_ownership(percentage, contributors, config)

    for contributor, contribution in ownership.items():
        print(f"Files owned by {CONTRIBUTOR} {contributor.name}")
        for c in contribution:
            print(f"\t{c}")
        print(f"Total: {len(contribution)} for {CONTRIBUTOR} {contributor}")

    return percentage, ownership


def display_dir_tree(percentage: Percentage, repo: Repo):
    header(f"{DIRECTORY_TREE} Dir Tree with ownership:")

    triples = []

    for key in percentage.file_per_contributor.keys():
        for name, percent in percentage.file_per_contributor[key]:
            triples.append((Path(os.path.relpath(key, repo.working_dir)), percent, name))

    tree = build_tree(triples)
    print_tree(tree)


def rule_info(config: Configuration, ownership: Dict[Contributor, List[ContributionDistribution]]):
    header(f"{RULES} Rules: ")

    for rule in config.parsed_rules.rules:
        print(rule)

    print()
    header(f"{VIOLATED_RULES} Violated Rules: ")

    rule_result = config.parsed_rules.matches(ownership)

    for c, rules in rule_result.items():
        rules_format = [('\t' + str(rule) + os.linesep) for rule in rules]
        print(f"{ERROR} Contributor {c} did not fulfill the following requirements:")
        print("".join(rules_format), end='')


def syntax_info():
    header(f"{SYNTAX} Syntax:")
    print(f"{INFO} TODO")


def semantic_info(tracked_files: List[FileGroup],
                  ownership: Dict[Contributor, List[ContributionDistribution]],
                  semantics: List[List[Tuple[SemanticWeightModel, 'LangElement']]]):
    header(f"{SEMANTICS} Semantics:")

    for i in range(len(tracked_files)):
        group = tracked_files[i]
        group_sem = semantics[i]
        print(f"{FILE_GROUP} Group: {group.name}")
        print(f"Total files: {len(group.files)}")
        total_weight = 0.0
        for j in range(len(group.files)):
            if not group_sem or group_sem[j][0].is_empty:
                continue

            owner = get_owner(ownership, group.files[j])
            print(f"File: {group.files[j].name}: Owner: {owner.name if owner is not None else 'None'}")
            structure = group_sem[j][1]
            print(f"Contents: Classes: {len(list(structure.classes))} "
                  f"Functions: {len(list(structure.functions))} "
                  f"Properties: {len(list(structure.properties))} "
                  f"Fields: {len(list(structure.fields))} "
                  f"Comments: {len(list(structure.comments))} ")
            weight = structure.compute_weight(group_sem[j][0])
            print(f"{WEIGHT} Total semantic weight: {weight}")
            total_weight += weight

        print(f"{WEIGHT} Total weight: {total_weight}")


def remote_info(commit_range: CommitRange, repo: Repo, config: Configuration, contributors: List[Contributor]) \
        -> Tuple[List[Tuple[float, List[Contributor]]], List[Tuple[float, List[Contributor]]]]:
    header(f"{REMOTE_REPOSITORY} Remote repository:")

    start_date = commit_range.hist_commit.committed_datetime
    end_date = commit_range.head_commit.committed_datetime

    remote_url = repo.remote(name=config.default_remote_name).url
    project = parse_project(remote_url, config.gitlab_access_token, config.github_access_token)

    remote_weight_model = RemoteRepositoryWeightModel.load()

    print(f"Project: {project.name}")
    print(f"{ISSUES} Total issues: {len(project.issues)}")
    print(f"{PULL_REQUESTS} Total pull requests: {len(project.pull_requests)}")
    print(f"{CONTRIBUTOR} Total contributors: {len(project.members)}")

    issue_weights: List[Tuple[float, List[Contributor]]] = []
    pr_weights: List[Tuple[float, List[Contributor]]] = []

    for issue in project.issues:
        header(f"{ISSUES} Issue: {issue.name} - by {issue.author}")
        print(f"Description: {issue.description}")
        print(f"State: {issue.state}")
        if issue.assigned_to:
            print(f"Assignee: {issue.assigned_to}")
        if issue.closed_at is not None:
            print(f"Closed at: {issue.closed_at} by {issue.closed_by}")
        issue_weight = remote_weight_model.evaluate(issue, start_date, end_date)
        beneficiaries = []
        assignee = find_contributor(contributors, issue.assigned_to)
        if assignee is not None:
            beneficiaries.append(assignee)
        author_contributor = find_contributor(contributors, issue.author)
        if author_contributor is not None:
            beneficiaries.append(author_contributor)
        issue_weights.append((issue_weight, beneficiaries))

        print(f"{WEIGHT} Weight {issue_weight} - Beneficiaries: {', '.join(map(lambda x: x.name, beneficiaries))}")

    for pr in project.pull_requests:
        header(f"{PULL_REQUESTS} Pull request: {pr.name} - by {pr.author}")
        print(f"From: {pr.source_branch} to {pr.target_branch}")
        print(f"Description: {pr.description}")
        print(f"State: {pr.merge_status}")
        if pr.merged_at is not None:
            print(f"Merged at: {pr.merged_at} by {pr.merged_by}")
        pr_weight = remote_weight_model.evaluate(pr, start_date, end_date)
        beneficiaries = []
        merger = find_contributor(contributors, pr.merged_by)
        if merger is not None:
            beneficiaries.append(merger)
        author_contributor = find_contributor(contributors, pr.author)
        if author_contributor is not None:
            beneficiaries.append(author_contributor)
        pr_weights.append((pr_weight, beneficiaries))
        print(f"{WEIGHT} Weight {pr_weight} - Beneficiaries: {', '.join(map(lambda x: x.name, beneficiaries))}")

    return issue_weights, pr_weights

def file_statistics_info(commit_range: CommitRange, contributors: List[Contributor])\
        -> Dict[str, FlaggedFiles]:
    file_flags = get_flagged_files_by_contributor([x for x in commit_range], contributors)
    for contributor in contributors:
        print(f"{CONTRIBUTOR} {contributor})")
        for key, count in file_flags[contributor.name].counts.items():
            print(f" => {key} - {count}")
    return file_flags


def display_results(repo: git.Repo,
                    commit_range: CommitRange,
                    syntax: AnalysisResult,
                    tracked_files: List[FileGroup],
                    semantics: List[List[Tuple[SemanticWeightModel, 'LangElement']]],
                    config: Configuration) -> None:
    set_repo(repo)

    contributors = display_contributor_info(commit_range, config)
    separator()
    _ = commit_info(commit_range, repo, contributors)
    separator()
    plot_commits([x for x in commit_range][1:], contributors, repo)
    separator()
    file_flags = file_statistics_info(commit_range, contributors)
    separator()
    percentage, ownership = percentage_info(syntax, contributors, config)
    separator()
    display_dir_tree(percentage, repo)
    separator()
    rule_info(config, ownership)
    separator()
    syntax_weights = syntax_info()
    separator()
    semantic_weights = semantic_info(tracked_files, ownership, semantics)
    separator()
    issue_weights, pr_weights = remote_info(commit_range, repo, config, contributors)
    separator()

if __name__ == '__main__':
    issue = Issue("", "", "", datetime.now(), None, "", "", "")
    assert isinstance(issue, Issue)
