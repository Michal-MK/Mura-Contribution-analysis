from typing import Tuple, List

import git

from configuration import Configuration
from history_analyzer import AnalysisResult, calculate_percentage, CommitRange
from lib import FileGroup, Contributor, get_contributors, set_repo, compute_file_ownership, find_contributor
from semantic_weight_model import SemanticWeightModel



def merge_results(repo: git.Repo,
                  range: CommitRange,
                  syntax: AnalysisResult,
                  tracked_files: List[FileGroup],
                  semantics: List[List[Tuple[SemanticWeightModel, float]]],
                  config: Configuration) -> None:
    set_repo(repo)

    contributors = get_contributors()

    for commit in range:
        author = repo.commit(commit).author.name
        if author is None:
            continue
        contributor = find_contributor(contributors, author)
        print(f'Commit: {commit} by {contributor.name}')


    percentage = calculate_percentage(syntax)

    print('Percentage of tracked files: {}'.format(percentage.global_contribution.items()))

    ownership = compute_file_ownership(percentage, contributors, config)

    ownership_result = config.parsed_rules.matches(ownership)

    for file, distribution in percentage.file_per_contributor.items():
        print(f'File: {file}: {[(x, y) for x, y in distribution]}')