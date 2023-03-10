from pathlib import Path
from typing import List


class Rule:
    def __init__(self, actor, directory, file, amount):
        self.actor = actor
        self.directory = directory
        self.file = file
        self.amount = amount

    @property
    def all_actors(self):
        return self.actor == "*"


def parse_rule_file(rule_definitions: Path) -> List[Rule]:
    if not rule_definitions.exists():
        raise Exception("Rule definitions file does not exist")

    rules = []

    with rule_definitions.open() as f:
        for line in f:
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
                        section_content.append(line[section_start:index])
                        section_start = index + 1
                if char == '\\':
                    if index + 1 < len(line):
                        if line[index + 1] == '"':
                            index += 1
                if char == '"':
                    in_quotes = not in_quotes
            rules.append(Rule(*section_content))
        return rules


def parse_rules(lines: List[str]) -> List[Rule]:
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
        rules.append(Rule(*section_content))
    return rules


if __name__ == '__main__':
    rules = parse_rules(['* "*/service/*" .*Service.*\.java >=1'])
    print(rules)
