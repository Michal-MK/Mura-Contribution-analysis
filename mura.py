from typing import Tuple, List

import git

from history_analyzer import AnalysisResult, calculate_percentage, CommitRange
from lib import FileGroup, Contributor, get_contributors, set_repo
from semantic_weight_model import SemanticWeightModel


def find_contributor(contributors: List[Contributor], author: str) -> Contributor:
    for contributor in contributors:
        if author == contributor.name:
            return contributor
        if author in contributor.aliases:
            return contributor
        if author in list(map(lambda x: x.name, contributor.aliases)):
            return contributor


    raise ValueError('Contributor not found')


def merge_results(repo: git.Repo,
                  range: CommitRange,
                  syntax: AnalysisResult,
                  tracked_files: List[FileGroup],
                  semantics: List[List[Tuple[SemanticWeightModel, float]]]) -> None:
    set_repo(repo)

    contributors = get_contributors()

    for commit in range:
        author = repo.commit(commit).author.name
        contributor = find_contributor(contributors, author)
        print(f'Commit: {commit} by {contributor.name}')


    percentage = calculate_percentage(syntax)

    print('Percentage of tracked files: {}'.format(percentage.global_contribution.items()))

    for file, distribution in percentage.file_per_contributor.items():
        print(f'File: {file}: {[(x, y) for x, y in distribution]}')