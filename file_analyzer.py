import json
import os
import re
from enum import Enum
from typing import List, Dict, Any
from pathlib import Path

import Levenshtein

from history_analyzer import FileSection
from semantic_analysis import compute_semantic_weight

loaded_weight_maps: Dict[str, 'WeightMap'] = {}

class PatternType(Enum):
    Literal = 1
    Regex = 2


class BlankLineHandler:
    __slots__ = ["count"]

    def __init__(self):
        self.count = 0

    def next(self) -> float:
        self.count += 1
        if self.count == 1:
            return 1
        elif self.count == 2:
            return 0.5
        else:
            return 0

    def clear(self):
        self.count = 0

class FileWeight:
    def __init__(self, file: Path, line_weights: List[float], semantic_weight: Dict[FileSection, float]):
        self.file = file
        self.line_weights = line_weights
        self.semantic_weight = semantic_weight

    @property
    def total_line_weight(self):
        return sum(self.line_weights)

    def final_weight(self):
        return self.total_line_weight

    @property
    def average_line_weight(self):
        return self.total_line_weight / len(self.line_weights)

    @property
    def maximum_achievable_line_weight(self):
        return len(self.line_weights)


class WeightMap:
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
        self.weights: List[WeightMap.Entry] = []

    def load(self, file):
        weight_map: List[Dict[str, Any]] = json.load(file)

        for entry in weight_map:
            self.weights.append(WeightMap.Entry(
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


def load_weight_map(file_path: Path) -> WeightMap:
    """
    Load the weight map for a file
    :param file_path: The file to load the weight map for
    :return: The weight map
    """
    suffix = file_path.suffix.lstrip('.')
    if suffix not in loaded_weight_maps:
        ret = WeightMap()
        with open(os.path.join(Path(__file__).parent, "weight-maps", suffix + ".json"), 'r') as f:
            ret.load(f)
        return ret
    else:
        return loaded_weight_maps[suffix]

def has_weight_map(file: Path) -> bool:
    if file.is_dir():
        return False
    suffix = file.suffix.lstrip('.')
    return os.path.isfile(os.path.join(Path(__file__).parent, "weight-maps", suffix + ".json"))

def compute_file_weight(file: Path) -> FileWeight:
    """
    Compute the weight of a file
    :param file: full path to the file
    :return: The weight of the file based on its contents
    """
    with open(file, 'r', encoding='UTF-8-SIG') as f:
        lines = f.readlines()
        line_weights = compute_lines_weight(file, lines)
        semantic_weight = compute_semantic_weight(file)
        return FileWeight(file, line_weights, semantic_weight)

def compute_lines_weight(file: Path, lines: List[str]):
    strip_chars = ' \t\r\n'
    weight_map = load_weight_map(file)
    blank_line_handler = BlankLineHandler()
    ret = []
    for line in lines:
        line = line.strip(strip_chars)
        if line == '':
            ret.append(blank_line_handler.next())
            continue
        blank_line_handler.clear()
        weight = weight_map.get_weight(line)
        ret.append(weight)
    return ret

