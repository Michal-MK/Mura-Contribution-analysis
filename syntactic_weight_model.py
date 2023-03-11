import json
import re
from typing import List, Dict, Any

import Levenshtein

from pattern_type import PatternType


class SyntacticWeightModel:
    class Entry:
        def __init__(self, pattern_type: PatternType, pattern: str, exactness: int, weight: int) -> None:
            self.pattern_type = pattern_type
            self.pattern = pattern
            self.exactness = exactness
            self.weight = weight
            self.regex_pattern = re.compile(pattern) if pattern_type == PatternType.Regex else None

        def matches(self, line: str) -> bool:
            """
            Decide whether the line matches the pattern of this entry
            """
            if self.pattern_type == PatternType.Literal:
                return Levenshtein.distance(self.pattern, line) <= self.exactness
            elif self.pattern_type == PatternType.Regex:
                assert self.regex_pattern is not None
                return self.regex_pattern.match(line) is not None
            return False  # Undefined case

    def __init__(self):
        self.base_weight = 1
        self.weights: List[SyntacticWeightModel.Entry] = []

    def load(self, file):
        weight_map: List[Dict[str, Any]] = json.load(file)

        for entry in weight_map:
            self.weights.append(SyntacticWeightModel.Entry(
                PatternType.Literal if entry["type"] == "Literal" else PatternType.Regex,
                entry["value"],
                entry["exactness"] if "exactness" in entry else 0,
                entry["weight"]
            ))

    def get_weight(self, line: str) -> float:
        for key in self.weights:
            if key.matches(line):
                return key.weight
        return self.base_weight
