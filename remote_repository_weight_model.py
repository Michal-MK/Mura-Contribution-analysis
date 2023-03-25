from pathlib import Path
from typing import Dict

from fs_access import parse_model_content

WEIGHT_MODELS: Dict[str, 'RemoteRepositoryWeightModel'] = {}


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
    def parse(provider: str) -> 'RemoteRepositoryWeightModel':
        if provider in WEIGHT_MODELS:
            return WEIGHT_MODELS[provider]

        weight_model = RemoteRepositoryWeightModel()
        base_weights = Path(__file__).parent / "remote-repo-weights" / "remote_repository_weights.txt"

        weight_model = parse_model_content(weight_model, base_weights)

        WEIGHT_MODELS[provider] = weight_model
        return weight_model
