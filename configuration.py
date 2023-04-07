import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import gitlab

from fs_access import parse_model_content
from rules import RuleCollection, parse_rule_file
from uni_chars import *


class Configuration:
    def __init__(self):
        self.full_ownership_min_threshold = 0.8
        self.ownership_min_threshold = 0.2
        self.rule_violation_multiplier = 0.9
        self.base_hour_match_weight = 200.0
        self.hour_estimate = 24.0
        self.remote_service = "https://gitlab.fi.muni.cz"
        self.gitlab_access_token = ""
        self.github_access_token = ""
        self.default_remote_name = "origin"
        self.default_branch = "master"
        self.ignore_remote_repo = False
        self.anonymous_mode = False
        self.ignored_extensions: List[str] = []

        self.contributor_map: Optional[List[Tuple[str, str]]] = None
        self.parsed_rules: RuleCollection = RuleCollection([])

    @staticmethod
    def load_from_file(config_path: Path, rules_path: Path, verbose=False) -> 'Configuration':
        ret = Configuration()
        if verbose:
            print(f"{INFO} Loading general configuration!")

        parse_model_content(ret, config_path)

        if verbose:
            print(f"{SUCCESS} General configuration loaded successfully!")

        if ret.gitlab_access_token == "" and 'GITLAB_ACCESS_TOKEN' in os.environ:
            ret.gitlab_access_token = os.environ['GITLAB_ACCESS_TOKEN']
        if ret.github_access_token == "" and 'GITHUB_ACCESS_TOKEN' in os.environ:
            ret.github_access_token = os.environ['GITHUB_ACCESS_TOKEN']

        if verbose:
            if ret.remote_service is not None and ret.gitlab_access_token != "":
                print(f"{INFO} GitLab access token found! It will be validated when repository is set!")
            if ret.remote_service is not None and ret.github_access_token != "":
                print(f"{INFO} GitHub access token found! It will be validated when repository is set!")

        if verbose:
            print(f"{INFO} Loading rules!")

        ret.parsed_rules = parse_rule_file(rules_path, verbose=verbose)

        if verbose:
            print(f"{SUCCESS} Rules loaded successfully!")

        return ret


def list_semantic_analyzers():
    def dump(info: List[str]):
        for line in info:
            print(line)
        print()

    print(f"{INFO} Semantic analyzers available:")
    semantics_path = Path("lang-semantics")
    for fsi in semantics_path.iterdir():
        info: List[str] = []
        if fsi.is_dir():
            info.append(f"{PLUS} Semantic analyzer for .{fsi.name} extension")
            target = fsi / "target"
            if target.exists():
                info.append(f"{LAUNCH} Launch command in 'target': {target.read_text(encoding='utf-8-sig')}")
            else:
                info.append(f"{ERROR} -> '{target}' does not exist! I have no idea how to launch this analyzer!")
                dump(info)
                continue
            setup = fsi / "setup"
            if setup.exists():
                info.append(f"{WARN} Setup file exists! It contains the following information:")
                info.append(f"{setup.read_text(encoding='utf-8-sig')}")
            dump(info)


def validate() -> 'Configuration':
    config_path = Path("configuration_data/configuration.txt")
    rules_path = Path("configuration_data/rules.txt")

    if not config_path.exists():
        raise FileNotFoundError(f"{ERROR} Path {config_path} does not exist!")
    if not config_path.is_file():
        raise FileNotFoundError(f"{ERROR} Path {config_path} is not a file!")

    if not rules_path.exists():
        raise FileNotFoundError(f"{ERROR} Path {rules_path} does not exist!")
    if not rules_path.is_file():
        raise FileNotFoundError(f"{ERROR} Path {rules_path} is not a file!")

    configuration = Configuration.load_from_file(config_path, rules_path, verbose=True)
    print(f"{SUCCESS} Configuration loaded successfully!")

    print()
    list_semantic_analyzers()

    return configuration


def open_configuration_folder():
    config_path = Path(__file__).parent / "test" / "configuration_data"
    if sys.platform == "win32":
        # Let's all have a laugh: https://answers.microsoft.com/en-us/windows/forum/all/windows-11-22h2-explorerexe-command-line-switch-to/b0958474-6124-44c9-b01a-7e6952317848
        os.system(f"explorer {config_path}")
    else:
        os.system(f"xdg-open {config_path}")
