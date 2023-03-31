import os
from pathlib import Path
from typing import List

from fs_access import parse_model_content
from rules import RuleCollection, parse_rule_file
from repository_hooks import parse_projects, RemoteRepository


class Configuration:
    def __init__(self):
        self.full_ownership_min_threshold = 0.8
        self.ownership_min_threshold = 0.2
        self.remote_service = "https://gitlab.fi.muni.cz"
        self.gitlab_access_token = ""
        self.github_access_token = ""
        self.default_remote_name = "origin"

        self.parsed_rules: RuleCollection = RuleCollection([])

    @staticmethod
    def load_from_file(config_path: Path, rules_path: Path) -> 'Configuration':
        ret = Configuration()
        parse_model_content(ret, config_path)
        if ret.gitlab_access_token == "" and 'GITLAB_ACCESS_TOKEN' in os.environ:
            ret.gitlab_access_token = os.environ['GITLAB_ACCESS_TOKEN']
        if ret.github_access_token == "" and 'GITHUB_ACCESS_TOKEN' in os.environ:
            ret.github_access_token = os.environ['GITHUB_ACCESS_TOKEN']
        ret.parsed_rules = parse_rule_file(rules_path)

        return ret