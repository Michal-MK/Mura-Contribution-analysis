'''
This file holds data structures and methods for the remote repository weight configuration.
'''

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from fs_access import parse_model_content
from repository_hooks import Issue, PR
from uni_chars import *

CACHE: Optional['RemoteRepositoryWeightModel'] = None


class RemoteRepositoryWeightModel:
    '''
    Class responsible for holding the configuration of the remote repository weight model.
    Calling `evaluate` with the appropriate parameters will display the weight of all Issues and PRs provided
    according to the model.
    '''
    def __init__(self):
        self.base_issue_weight = 0
        self.base_pr_weight = 0
        self.no_pr_review_multiplier = 0.0
        self.no_issue_activity_multiplier = 0.0
        self.stale_pr_multiplier = 0.0
        self.stale_pr_days = 0
        self.large_pr_multiplier = 0.0
        self.large_pr_commits = 0

    def evaluate(self, element: Union[Issue, PR], start_date: datetime, end_date: datetime, verbose=True) -> float:
        if isinstance(element, Issue):
            if element.created_at > end_date or element.closed_at is None or element.closed_at < start_date \
                    or element.closed_at > end_date:
                if verbose:
                    print(f"{INFO} Issue was not closed during the period or did not exist at all.")
                return 0.0
            weight = self.base_issue_weight
            # TODO
            return weight
        elif isinstance(element, PR):
            if element.created_at > end_date or element.merged_at is None or element.merged_at < start_date \
                    or element.merged_at > end_date:
                if verbose:
                    print(f"{INFO} PR was not merged during the period or did not exist at all.")
                return 0.0
            weight = self.base_pr_weight
            if element.author == element.merged_by and not element.reviewers:
                if verbose:
                    print(f"{WARN} PR {element.name} was merged by the author and has no reviewers!")
                weight = 0.0
            elif not element.reviewers:
                if verbose:
                    print(f"{WARN} PR {element.name} has no reviewers!")
                weight *= self.no_pr_review_multiplier
            if len(element.commit_shas) > self.large_pr_commits:
                if verbose:
                    print(f"{WARN} PR {element.name} has {len(element.commit_shas)} commits! (> {self.large_pr_commits}))")
                weight *= self.large_pr_multiplier
            if (element.created_at - element.merged_at).total_seconds() > self.stale_pr_days * 24 * 3600:
                if verbose:
                    print(f"{WARN} PR {element.name} is stale! (> {self.stale_pr_days} days)")
                weight *= self.stale_pr_multiplier
            return weight

    @staticmethod
    def load() -> 'RemoteRepositoryWeightModel':
        global CACHE
        if CACHE is not None:
            return CACHE

        weight_model = RemoteRepositoryWeightModel()
        base_weights = Path(__file__).parent / "remote-repo-weights" / "weights.txt"

        weight_model = parse_model_content(weight_model, base_weights)

        CACHE = weight_model
        return CACHE
