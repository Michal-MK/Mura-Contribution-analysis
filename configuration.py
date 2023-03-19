from pathlib import Path

from fs_access import parse_model_content
from rules import RuleCollection, parse_rule_file


class Configuration:
    def __init__(self):
        self.full_ownership_min_threshold = 0.8
        self.ownership_min_threshold = 0.2

        self.parsed_rules: RuleCollection = RuleCollection([])

    @staticmethod
    def load_from_file(config_path: Path, rules_path: Path) -> 'Configuration':
        ret = Configuration()
        ret.parsed_rules = parse_rule_file(rules_path)
        parse_model_content(ret, config_path)

        return ret