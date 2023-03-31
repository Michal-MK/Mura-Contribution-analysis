import os
from typing import Tuple, List, Dict, Optional

import git

from configuration import Configuration
from history_analyzer import AnalysisResult, calculate_percentage, CommitRange
from lib import FileGroup, Contributor, get_contributors, set_repo, compute_file_ownership, find_contributor
from repository_hooks import parse_project
from semantic_analysis import LangElement
from semantic_weight_model import SemanticWeightModel

from pathlib import Path
from collections import defaultdict


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
                print(f'{prefix}{connector}{name} [{owners_str}]')
                if connector == '└── ':
                    print(f'{prefix}')
            else:
                owners_str = ', '.join([f'{owner}: {value * 100:.0f}%' for owner, value in
                                        calculate_ownership(value, ownership_cache).items()])
                print(f'{prefix}{connector}{name} [{owners_str}]')
                print_tree(value, level + 1, new_prefix, ownership_cache)


def separator() -> None:
    print("============================================")
    print()


def header(text: str) -> None:
    print(text)
    print()


def merge_results(repo: git.Repo,
                  commit_range: CommitRange,
                  syntax: AnalysisResult,
                  tracked_files: List[FileGroup],
                  semantics: List[List[Tuple[SemanticWeightModel, 'LangElement']]],
                  config: Configuration) -> None:
    set_repo(repo)

    contributors = get_contributors(range=commit_range)

    header("Contributors:")

    for c in contributors:
        print(c)

    separator()
    header(f"Total commits: {len(commit_range.compute_path())}")

    commit_distribution: Dict[Contributor, int] = defaultdict(lambda: 0)

    for commit in commit_range:
        author = repo.commit(commit).author.name
        if author is None:
            continue
        contributor = find_contributor(contributors, author)
        commit_distribution[contributor] += 1
        print(f'Commit: {commit} by {contributor.name}')

    separator()
    header(f"Commits per contributor:")

    for c, count in commit_distribution.items():
        print(f"{count} commits by: {c}")

    assert sum(commit_distribution.values()) == len(commit_range.compute_path())

    separator()
    header('Percentage of tracked files:')

    percentage = calculate_percentage(syntax)

    for c, p in percentage.global_contribution.items():
        # print the contribution of each contributor formatted as a percentage
        print(f'\t{c}: {p:.2%}')

    ownership = compute_file_ownership(percentage, contributors, config)

    def get_owner(file: Path) -> Optional[Contributor]:
        for k, v in ownership.items():
            if file in v:
                return k
        return None

    for contributor, contribution in ownership.items():
        print(f"Files owned by {contributor.name}")
        for c in contribution:
            print(f"\t{c}")
        print(f"Total: {len(contribution)} for {contributor}")

    separator()
    header("Dir Tree with ownership:")

    triples = []

    for key in percentage.file_per_contributor.keys():
        for name, percent in percentage.file_per_contributor[key]:
            triples.append((Path(os.path.relpath(key, repo.working_dir)), percent, name))

    tree = build_tree(triples)
    print_tree(tree)

    separator()
    header("Rules: ")

    rule_result = config.parsed_rules.matches(ownership)

    for c, rules in rule_result.items():
        rules_format = [('\t' + str(rule) + os.linesep) for rule in rules]
        print(f"Contributor {c} did not fulfill the following requirements:{os.linesep}")
        print("".join(rules_format), end='')

    for file, distribution in percentage.file_per_contributor.items():
        print(f'File: {file}: {[(x, y) for x, y in distribution]}')

    separator()
    header("Semantics:")

    for i in range(len(tracked_files)):
        group = tracked_files[i]
        group_sem = semantics[i]
        print(f"Group: {group.name}")
        print(f"Total files: {len(group.files)}")
        total_weight = 0.0
        for j in range(len(group.files)):
            if not group_sem or group_sem[j][0].is_empty:
                continue

            print(f"File: {group.files[j].name}: Owner: {get_owner(group.files[j])}")
            structure = group_sem[j][1]
            print(f"Contents: Classes: {len(list(structure.classes))} "
                  f"Functions: {len(list(structure.functions))} "
                  f"Properties: {len(list(structure.properties))} "
                  f"Fields: {len(list(structure.fields))} "
                  f"Comments: {len(list(structure.comments))} ")
            weight = structure.compute_weight(group_sem[j][0])
            print(f"Total semantic weight: {weight}")
            total_weight += weight

        print(f"Total weight: {total_weight}")

    separator()
    header("Remote repository:")

    remote_url = repo.remote(name=config.default_remote_name).url
    project = parse_project(remote_url, config.gitlab_access_token, config.github_access_token)

    print(f"Project: {project.name}")
    print(f"Total issues: {len(project.issues)}")
    print(f"Total pull requests: {len(project.pull_requests)}")
    print(f"Total contributors: {len(project.members)}")

    for issue in project.issues:
        print(f"Issue: {issue.name} - by {issue.author}")
        print(f"Description: {issue.description}")
        print(f"State: {issue.state}")
        if issue.assigned_to:
            print(f"Assignee: {issue.assigned_to}")
        if issue.closed_at is not None:
            print(f"Closed at: {issue.closed_at} by {issue.closed_by}")

    for pr in project.pull_requests:
        print(f"Pull request: {pr.name} - by {pr.author}")
        print(f"From: {pr.source_branch} to {pr.target_branch}")
        print(f"Description: {pr.description}")
        print(f"State: {pr.merge_status}")
        if pr.merged_at is not None:
            print(f"Merged at: {pr.merged_at} by {pr.merged_by}")
