from pathlib import Path
from typing import Optional

from fs_access import parse_model_content

CACHE: Optional['RemoteRepositoryWeightModel'] = None


class RemoteRepositoryWeightModel:
    def __init__(self):
        self.base_issue_weight = 0
        self.base_pr_weight = 0
        self.no_pr_review_multiplier = 0.0
        self.no_issue_activity_multiplier = 0.0
        self.stale_pr_multiplier = 0.0
        self.stale_pr_days = 0
        self.large_pr_multiplier = 0.0
        self.large_pr_commits = 0

    @staticmethod
    def load() -> 'RemoteRepositoryWeightModel':
        global CACHE
        if CACHE is not None:
            return CACHE

        weight_model = RemoteRepositoryWeightModel()
        base_weights = Path(__file__).parent / "remote-repo-weights" / "remote_repository_weights.txt"

        weight_model = parse_model_content(weight_model, base_weights)

        CACHE = weight_model
        return CACHE
