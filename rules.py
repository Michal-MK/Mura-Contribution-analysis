from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import List, Dict

from lib import ContributionDistribution, Contributor, repo_p
from uni_chars import *


class RuleOp(Enum):
    EQUALS = 1
    GREATER_THAN = 2
    GREATER_THAN_OR_EQUALS = 3
    LESS_THAN = 4
    LESS_THAN_OR_EQUALS = 5


class Rule:
    def __init__(self, contributor: str, directory: str, file: str, amount: str):
        self.contributor = contributor
        if directory.startswith("\""):
            if not directory.endswith("\""):
                raise Exception("Invalid directory")
            self.directory = directory[1:-1]
            if self.directory.endswith("/"):
                self.directory = self.directory[:-1]
        if file.startswith("\""):
            if not file.endswith("\""):
                raise Exception("Invalid file")
            self.file = re.compile(file[1:-1])
        try:
            self.amount = int(amount)
            self.op_call = lambda x, y: x == y
            self.op = RuleOp.EQUALS
        except ValueError:
            if amount.startswith(">="):
                self.amount = int(amount[2:])
                self.op_call = lambda val, req: val >= req
                self.op = RuleOp.GREATER_THAN_OR_EQUALS
            elif amount.startswith("<="):
                self.amount = int(amount[2:])
                self.op_call = lambda val, req: val <= req
                self.op = RuleOp.LESS_THAN_OR_EQUALS
            elif amount.startswith(">"):
                self.amount = int(amount[1:])
                self.op_call = lambda val, req: val > req
                self.op = RuleOp.GREATER_THAN
            elif amount.startswith("<"):
                self.amount = int(amount[1:])
                self.op_call = lambda val, req: val < req
                self.op = RuleOp.LESS_THAN
            else:
                raise Exception("Invalid amount")

    @property
    def all_contributors(self):
        return self.contributor == "*"

    def matches(self, ownership: List[ContributionDistribution]) -> bool:
        for file, percentage in ownership:
            repo_path = repo_p(file) # TODO do not rely on lib.REPO

            if repo_path.parent.match(self.directory) and self.file.match(repo_path.name):
                if self.op_call(percentage, self.amount):
                    return True
        return False

    def __str__(self):
        ret = ""
        if self.all_contributors:
            ret += "All contributors "
        else:
            ret += f"{self.contributor} "
        ret += f"must have "
        if self.op == RuleOp.EQUALS:
            ret += f"exactly {self.amount} "
        elif self.op == RuleOp.GREATER_THAN_OR_EQUALS:
            ret += f"at least {self.amount} "
        elif self.op == RuleOp.LESS_THAN_OR_EQUALS:
            ret += f"at most {self.amount} "
        elif self.op == RuleOp.GREATER_THAN:
            ret += f"more than {self.amount} "
        elif self.op == RuleOp.LESS_THAN:
            ret += f"less than {self.amount} "
        ret += f"file/s matching: `{self.file.pattern}` in a directory matching: `{self.directory}`"
        return ret


class RuleCollection:
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def matches(self, ownership: Dict[Contributor, List[ContributionDistribution]]) -> Dict[Contributor, List[Rule]]:
        """
        Matches the rule_data against the ownership, returning a dictionary of contributors and the rule_data that they violate.

        :param ownership: The ownership to match against
        :return: A dictionary of contributors and the rule_data that they violate
        """
        ret: Dict[Contributor, List[Rule]] = {}
        for actor in ownership.keys():
            for rule in self.rules:
                if rule.all_contributors or rule.contributor == actor:
                    if not rule.matches(ownership[actor]):
                        if actor not in ret:
                            ret[actor] = []
                        ret[actor].append(rule)
        return ret


def parse_rule_file(rule_definitions: Path, verbose=False) -> RuleCollection:
    if not rule_definitions.exists():
        raise Exception(f"{ERROR} Rule definitions file {rule_definitions} does not exist")

    with rule_definitions.open() as f:
        lines = f.readlines()
        return parse_rules(lines, verbose)


def parse_rules(lines: List[str], verbose=False) -> RuleCollection:
    rules = []
    for line in lines:
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue

        section_start = 0
        section_content = []

        in_quotes = False
        index = 0
        while index < len(line):
            char = line[index]
            if char == ' ':
                if not in_quotes:
                    section_end = index
                    section_content.append(line[section_start:section_end])
                    section_start = index + 1
            if char == '\\':
                if index + 1 < len(line):
                    if line[index + 1] == '"':
                        index += 1
            if char == '"':
                in_quotes = not in_quotes
            index += 1

        section_content.append(line[section_start:])
        rule = Rule(*section_content)

        if verbose:
            print(f" - Rule: {rule}")

        rules.append(rule)

    if verbose:
        print()

    return RuleCollection(rules)
