import os
from collections import defaultdict
from pathlib import Path
from typing import Tuple, List, Dict, Optional

import git

from configuration import Configuration
from history_analyzer import AnalysisResult, calculate_percentage, CommitRange
from lib import FileGroup, Contributor, get_contributors, set_repo, compute_file_ownership, find_contributor
from repository_hooks import parse_project
from semantic_analysis import LangElement
from semantic_weight_model import SemanticWeightModel



def merge_results(repo: git.Repo,
                  commit_range: CommitRange,
                  syntax: AnalysisResult,
                  tracked_files: List[FileGroup],
                  semantics: List[List[Tuple[SemanticWeightModel, 'LangElement']]],
                  config: Configuration) -> None:
    set_repo(repo)

    contributors = get_contributors(range=commit_range)

    print("Contributors:")
    for c in contributors:
        print(c)

    print(f"Total commits: {len(commit_range.compute_path())}")

    commit_distribution: Dict[Contributor, int] = defaultdict(lambda: 0)

    for commit in commit_range:
        author = repo.commit(commit).author.name
        if author is None:
            continue
        contributor = find_contributor(contributors, author)
        commit_distribution[contributor] += 1
        print(f'Commit: {commit} by {contributor.name}')

    for c, count in commit_distribution.items():
        print(f"{count} commits by: {c}")

    assert sum(commit_distribution.values()) == len(commit_range.compute_path())

    percentage = calculate_percentage(syntax)

    print('Percentage of tracked files: {}'.format(percentage.global_contribution.items()))

    ownership = compute_file_ownership(percentage, contributors, config)

    def get_owner(file: Path) -> Optional[Contributor]:
        for k ,v in ownership.items():
            if file in v:
                return k
        return None

    for contributor, contribution in ownership.items():
        print(f"Files: {map(lambda x: x.file, contribution)} owned by {contributor}")
        print(f"Total: {len(contribution)} for {contributor}")

    rule_result = config.parsed_rules.matches(ownership)

    for c, rules in rule_result.items():
        rules_format = [('\t' + str(rule) + os.linesep) for rule in rules]
        print(f"Contributor {c} did not fulfill the following requirements:{os.linesep}")
        print("".join(rules_format), end='')

    for file, distribution in percentage.file_per_contributor.items():
        print(f'File: {file}: {[(x, y) for x, y in distribution]}')

    print("Semantics:")
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

    remote_url = repo.remote(name=config.default_remote_name).url
    project = parse_project(remote_url, config.gitlab_access_token, config.github_access_token)

    if project is None:
        print("No project found for remote url: {}".format(remote_url))
        return

    print("Github projects not supported.")
