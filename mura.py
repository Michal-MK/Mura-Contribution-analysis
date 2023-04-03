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

ContributorWeight = Dict[Contributor, float]
GlobalRuleWeightMultiplier = Dict[Contributor, float]


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
                owners_str = ', '.join([f'{owner.name}: {value * 100:.0f}%' for owner, value in value.items()])
                print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
            else:
                sub_ownerships = [calculate_ownership(v, ownership_cache) for v in value.values() if
                                  isinstance(v, dict)]
                if len(sub_ownerships) > 0 \
                        and all(sub_ownerships[0] == sub_ownership for sub_ownership in sub_ownerships):
                    print(f'{prefix}{connector}{name}')
                else:
                    owners_str = ', '.join([f'{owner.name}: {value * 100:.0f}%' for owner, value in
                                            calculate_ownership(value, ownership_cache).items()])
                    print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
                print_tree(value, level + 1, new_prefix, ownership_cache)


def plot_commits(commits: List[str], commit_range: CommitRange, contributors: List[Contributor], repo: Repo,
                 force_x_axis_labels=False) -> None:
    commit_data = defaultdict(list)
    min_date = datetime.max.replace(tzinfo=timezone.utc)
    max_date = datetime.min.replace(tzinfo=timezone.utc)

    for commit in commits:
        commit_obj = commit_range.commit(commit)
        for contributor in contributors:
            if contributor == commit_obj.author:
                committed_date = commit_obj.committed_datetime
                commit_data[contributor.name].append(date2num(committed_date))
                min_date = min(min_date, committed_date)
                max_date = max(max_date, committed_date)
                break

    plt.figure(figsize=(12, 6))

    for name, dates in commit_data.items():
        plt.plot_date(sorted(dates), range(len(dates)), label=name)
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
    contributors = get_contributors(config, commit_range=commit_range)
    header(f"{CONTRIBUTOR} Contributors:")

    for contrib in contributors:
        print(contrib)

    return contributors


def commit_info(commit_range: CommitRange, repo: Repo, contributors: List[Contributor]) \
        -> Tuple[Dict[Contributor, int], List[Tuple[Contributor, int, int]]]:
    header(f"{COMMIT} Total commits: {len(commit_range.compute_path())}")

    commit_distribution: Dict[Contributor, int] = defaultdict(lambda: 0)

    for commit in commit_range:
        author = commit_range.commit(commit).author.name
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

    insertions_deletions = []

    for contrib in contributors:
        insertion, deletion = stats_for_contributor(contrib, commit_range)
        print(f"{CONTRIBUTOR} {contrib.name}: inserted '{insertion}' lines and deleted '{deletion}' lines.")
        insertions_deletions.append((contrib, insertion, deletion))

    return commit_distribution, insertions_deletions


def insertions_deletions_info(insertions_deletions: List[Tuple[Contributor, int, int]]) -> None:
    insertions_deletions.sort(key=lambda x: x[1], reverse=True)

    contributor_names = [x[0].name for x in insertions_deletions]
    insertions = [x[1] for x in insertions_deletions]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    ax1.pie(insertions, labels=contributor_names, autopct='%1.1f%%')
    ax1.set_title('Insertions')

    # Sort data in descending order by deletions
    insertions_deletions.sort(key=lambda x: x[2], reverse=True)

    contributor_names = [x[0].name for x in insertions_deletions]
    deletions = [x[2] for x in insertions_deletions]

    ax2.pie(deletions, labels=contributor_names, autopct='%1.1f%%')
    ax2.set_title('Deletions')

    fig.subplots_adjust(wspace=0.5)

    plt.show()


def percentage_info(syntax: AnalysisResult, contributors: List[Contributor], config: Configuration) \
        -> Tuple[Percentage, Dict[Contributor, List[ContributionDistribution]]]:
    header(f'{PERCENTAGE} Percentage of tracked files:')

    percentage = calculate_percentage(contributors, syntax)

    for contributor_name, percent in percentage.global_contribution.items():
        print(f'\t{contributor_name}: {percent:.2%}')

    ownership = compute_file_ownership(percentage, contributors, config)

    for contributor, contribution in ownership.items():
        print(f"Files owned by {CONTRIBUTOR} {contributor.name}")
        for contrib_distribution in contribution:
            print(f"\t{contrib_distribution}")
        print(f"Total: {len(contribution)} for {CONTRIBUTOR} {contributor}")

    return percentage, ownership


def display_dir_tree(config: Configuration, percentage: Percentage, repo: Repo):
    header(f"{DIRECTORY_TREE} Dir Tree with ownership:")

    triples = []

    for key in percentage.file_per_contributor.keys():
        for name, percent in percentage.file_per_contributor[key]:
            triples.append((Path(os.path.relpath(key, repo.working_dir)), percent, name))

    tree = build_tree(triples)
    print_tree(tree)


def rule_info(config: Configuration, ownership: Dict[Contributor, List[ContributionDistribution]]) \
        -> GlobalRuleWeightMultiplier:
    header(f"{RULES} Rules: ")

    ret: GlobalRuleWeightMultiplier = defaultdict(lambda: 1.0)

    for rule in config.parsed_rules.rules:
        print(rule)

    print()
    header(f"{VIOLATED_RULES} Violated Rules: ")

    rule_result = config.parsed_rules.matches(ownership)

    for c, rules in rule_result.items():
        rules_format = [('\t' + str(rule) + os.linesep) for rule in rules]
        print(f"{ERROR} Contributor {c} did not fulfill the following requirements:")
        print("".join(rules_format), end='')
        ret[c] *= config.rule_violation_multiplier

    return ret


def syntax_info() -> Dict[Contributor, float]:
    header(f"{SYNTAX} Syntax:")
    print(f"{INFO} TODO")
    return defaultdict(lambda: 0.0)


def semantic_info(tracked_files: List[FileGroup],
                  ownership: Dict[Contributor, List[ContributionDistribution]],
                  semantics: List[List[Tuple[SemanticWeightModel, 'LangElement']]]) \
        -> ContributorWeight:
    header(f"{SEMANTICS} Semantics:")

    contributor_weight: ContributorWeight = defaultdict(lambda: 0.0)

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
            print(f"{WEIGHT} Semantic file weight: {weight}")
            if owner is not None:
                contributor_weight[owner] += weight
            total_weight += weight

        print(f"{WEIGHT} Total weight: {total_weight}")

    return contributor_weight


def remote_info(commit_range: CommitRange, repo: Repo, config: Configuration, contributors: List[Contributor]) \
        -> ContributorWeight:
    header(f"{REMOTE_REPOSITORY} Remote repository management:")

    if config.ignore_remote_repo:
        print(f"{INFO} Skipping as 'config.ignore_remote_repo = True'")
        return {}

    start_date = commit_range.hist_commit.committed_datetime
    end_date = commit_range.head_commit.committed_datetime

    remote_url = repo.remote(name=config.default_remote_name).url
    project = parse_project(remote_url, config.gitlab_access_token, config.github_access_token)

    remote_weight_model = RemoteRepositoryWeightModel.load()

    print(f"Project: {project.name}")
    print(f"{ISSUES} Total issues: {len(project.issues)}")
    print(f"{PULL_REQUESTS} Total pull requests: {len(project.pull_requests)}")
    print(f"{CONTRIBUTOR} Total contributors: {len(project.members)}")

    contributor_weight: ContributorWeight = defaultdict(lambda: 0.0)

    for issue in project.issues:
        author_contributor = find_contributor(contributors, issue.author)
        header(f"{ISSUES} Issue: {issue.name} - by "
               f"{author_contributor.name if author_contributor is not None else 'None'}")
        print(f"Description: {issue.description}")
        print(f"State: {issue.state}")
        assignee = find_contributor(contributors, issue.assigned_to)
        closer = find_contributor(contributors, issue.closed_by)
        if issue.assigned_to:
            print(f"Assignee: {assignee.name if assignee is not None else 'None'}")
        if issue.closed_at is not None:
            print(f"Closed at: {issue.closed_at} by "
                  f"{closer.name if closer is not None else 'None'}")
        issue_weight = remote_weight_model.evaluate(issue, start_date, end_date)
        beneficiaries = []
        if assignee is not None:
            beneficiaries.append(assignee)
            contributor_weight[assignee] += issue_weight
        if closer is not None:
            beneficiaries.append(closer)
            contributor_weight[closer] += issue_weight
        if author_contributor is not None:
            beneficiaries.append(author_contributor)
            contributor_weight[author_contributor] += issue_weight

        print(f"{WEIGHT} Weight {issue_weight} - Beneficiaries: {', '.join(map(lambda x: x.name, beneficiaries))}")

    for pr in project.pull_requests:
        author_contributor = find_contributor(contributors, pr.author)
        header(f"{PULL_REQUESTS} Pull request: {pr.name} - by "
               f"{(author_contributor.name if author_contributor is not None else 'None')}")
        print(f"From: {pr.source_branch} to {pr.target_branch}")
        print(f"Description: {pr.description}")
        print(f"State: {pr.merge_status}")
        merger = find_contributor(contributors, pr.merged_by)
        if pr.merged_at is not None:
            print(f"Merged at: {pr.merged_at} by "
                  f"{merger.name if merger is not None else 'None'}")
        pr_weight = remote_weight_model.evaluate(pr, start_date, end_date)
        beneficiaries = []
        if merger is not None:
            beneficiaries.append(merger)
            contributor_weight[merger] += pr_weight
        author_contributor = find_contributor(contributors, pr.author)
        if author_contributor is not None:
            beneficiaries.append(author_contributor)
            contributor_weight[author_contributor] += pr_weight

        print(f"{WEIGHT} Weight {pr_weight} - Beneficiaries: {', '.join(map(lambda x: x.name, beneficiaries))}")

    return contributor_weight


def file_statistics_info(commit_range: CommitRange, contributors: List[Contributor]) \
        -> Dict[str, FlaggedFiles]:
    file_flags = get_flagged_files_by_contributor(commit_range, contributors)
    for contributor in contributors:
        print(f"{CONTRIBUTOR} {contributor})")
        for key, count in file_flags[contributor.name].counts.items():
            print(f" => {key} - {count}")
    return file_flags


def blanks_comments_info(commit_range: CommitRange, history_analysis_result: AnalysisResult,
                         tracked_files: List[FileGroup], contributors: List[Contributor]):
    header(f"{BLANKS_COMMENTS} Blanks and comments:")
    history_analysis_result
    return None


def summary_info(contributors: List[Contributor],
                 syntactic_weights: ContributorWeight,
                 semantic_weights: ContributorWeight,
                 repo_management_weights: ContributorWeight,
                 global_rule_weight_multiplier: GlobalRuleWeightMultiplier) -> None:
    sums: Dict[Contributor, float] = defaultdict(lambda: 0.0)

    def print_section(section: ContributorWeight, add=True):
        if not section:
            print(f'{INFO} Nothing to show here...')
            return

        for contributor in contributors:
            if contributor in section:
                print(f" -> {contributor.name}: {section[contributor]}")
                if add:
                    sums[contributor] = section[contributor]

    separator()
    print(f"{WEIGHT} Total weight per contributor for {SYNTAX} Syntax:")
    print_section(syntactic_weights)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {SEMANTICS} Semantics:")
    print_section(semantic_weights)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {REMOTE_REPOSITORY} Remote repository management:")
    print_section(repo_management_weights)

    separator()
    print(f"{WEIGHT}{WARN} Weight multiplier for unfulfilled {RULES} Rules:")
    print_section(global_rule_weight_multiplier, add=False)

    separator()
    print(f"{WEIGHT} Total weight per contributor:")

    for contributor in sums:
        sums[contributor] *= global_rule_weight_multiplier[contributor]

    position = 1
    for model in sorted(sums.items(), key=lambda x: x[1], reverse=True):
        assert isinstance(model, tuple)
        char = NUMBERS[position] if position <= len(NUMBERS) else f"{position}."
        print(f"{char} -> {model[0].name}: {model[1]}")
        position += 1


def display_results(repo: git.Repo,
                    commit_range: CommitRange,
                    syntax: AnalysisResult,
                    tracked_files: List[FileGroup],
                    semantics: List[List[Tuple[SemanticWeightModel, 'LangElement']]],
                    config: Configuration) -> None:
    set_repo(repo)

    contributors = display_contributor_info(commit_range, config)
    separator()
    commit_distribution, insertions_deletions = commit_info(commit_range, repo, contributors)
    separator()
    plot_commits([x for x in commit_range][1:], commit_range, contributors, repo)
    separator()
    file_flags = file_statistics_info(commit_range, contributors)
    separator()
    percentage, ownership = percentage_info(syntax, contributors, config)
    separator()
    display_dir_tree(config, percentage, repo)
    separator()
    global_rule_weight_multiplier = rule_info(config, ownership)
    separator()
    syntax_weights = syntax_info()
    separator()
    semantic_weights = semantic_info(tracked_files, ownership, semantics)
    separator()
    repo_management_weights = remote_info(commit_range, repo, config, contributors)
    separator()
    summary_info(syntax_weights, semantic_weights, repo_management_weights, global_rule_weight_multiplier)


if __name__ == '__main__':
    issue = Issue("", "", "", datetime.now(), None, "", "", "")
    assert isinstance(issue, Issue)
