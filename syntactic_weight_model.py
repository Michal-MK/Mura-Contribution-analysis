import json
import re
from pathlib import Path
from typing import List, Dict, Any, TextIO

import Levenshtein

from pattern_type import PatternType


class SyntacticWeightModel:
    class Entry:
        def __init__(self, pattern_type: PatternType, pattern: str, exactness: float, weight: float) -> None:
            self.pattern_type = pattern_type
            self.pattern = pattern
            self.match_distance = exactness
            self.weight = weight
            self.regex_pattern = re.compile(pattern) if pattern_type == PatternType.Regex else None

        def matches(self, line: str) -> bool:
            """
            Decide whether the line matches the pattern of this entry
            """
            if self.pattern_type == PatternType.Literal:
                return Levenshtein.distance(self.pattern, line) <= self.match_distance
            elif self.pattern_type == PatternType.Regex:
                assert self.regex_pattern is not None
                return self.regex_pattern.match(line) is not None
            return False  # Undefined case

    def __init__(self):
        self.base_weight = 1
        self.weights: List[SyntacticWeightModel.Entry] = []

    def load_literals(self, file: TextIO):
        for line in file.readlines():
            if not line.strip() or line.startswith('#'):
                continue
            split = line.split(',', maxsplit=3)
            assert len(split) == 3
            weight = float(split[0])
            exactness = float(split[1])
            pattern = split[2]
            self.weights.append(SyntacticWeightModel.Entry(PatternType.Literal, pattern, exactness, weight))

    def load_regex(self, file: TextIO):
        for line in file:
            if not line.strip() or line.startswith('#'):
                continue
            split = line.split(',', maxsplit=2)
            assert len(split) == 2
            pattern = split[1].strip()
            assert pattern.startswith('"') and pattern.endswith('"'), f"Patterns must be enclosed in \"\"! - {pattern}"
            self.weights.append(SyntacticWeightModel.Entry(PatternType.Regex, pattern[1:-1], 0, float(split[0])))


    def get_weight(self, line: str, line_stripped: str) -> float:
        for key in self.weights:
            if key.pattern_type == PatternType.Regex and key.matches(line) or \
               key.pattern_type == PatternType.Literal and key.matches(line_stripped):
                return key.weight
        return self.base_weight
