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
        self.access_token = ""

        self.parsed_rules: RuleCollection = RuleCollection([])
        self.projects: List[RemoteRepository] = []

    @staticmethod
    def load_from_file(config_path: Path, rules_path: Path, projects_path: Path) -> 'Configuration':
        ret = Configuration()
        parse_model_content(ret, config_path)
        if ret.access_token == "" and 'GITLAB_ACCESS_TOKEN' in os.environ:
            ret.access_token = os.environ['GITLAB_ACCESS_TOKEN']
        ret.parsed_rules = parse_rule_file(rules_path)
        ret.projects = parse_projects(projects_path, ret.access_token)

        return ret