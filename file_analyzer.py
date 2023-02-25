import json
import os
import re
from enum import Enum
from typing import List, Dict, Any
from pathlib import Path

import Levenshtein

from history_analyzer import FileSection

ignore_list = os.path.join(Path(__file__).parent, "data", "ignore-list.txt")
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


class FileGroup:
    def __init__(self, name: str, files: List[Path]):
        self.name = name
        self.files = files

    def get_common_extension(self):
        extensions = []
        for file in self.files:
            extensions.append(file.suffix)
        return max(set(extensions), key=extensions.count)


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


def _ignored_files() -> List[str]:
    """
    Get a list of all ignored files
    :return: A list of all ignored files
    """
    ret: List[str] = []
    with open(ignore_list, 'r') as f:
        for line in f:
            if line.isspace() or line.startswith('#') \
                    or line.startswith('/'):  # This is not supported by `pathlib.Path.rglob`
                continue
            ret.append(line.strip())
    return ret


def get_tracked_files(project_root: Path) -> List[FileGroup]:
    """
    Find all files that are related, relative to the project root
    :param project_root: The root directory of the project
    :return: A dictionary of all directories and their files which are related to each other
    """
    ret: List[FileGroup] = []

    for root, dirs, files in os.walk(project_root):
        to_remove = []
        for directory in dirs:
            if is_ignored(Path(root).joinpath(directory)) or directory == '.git':
                to_remove.append(directory)
        for directory in to_remove:
            dirs.remove(directory)
        file_group = FileGroup(root, [])
        for file in files:
            if is_ignored(Path(root).joinpath(file)):
                continue
            file_group.files.append(Path(root).joinpath(file))
        if file_group.files:
            ret.append(file_group)

    return ret


def is_ignored(file: Path) -> bool:
    """
    Check if a file is ignored
    :param file: The file to check
    :return: True if the file is ignored, False otherwise
    """
    ignored = _ignored_files()
    for ignore in ignored:
        if file.match(ignore):
            return True
    return False


def filter_related_groups(groups: List[FileGroup]) -> List[FileGroup]:
    """
    Filter groups such that only groups with a high file similarity are returned
    :param groups: A list of all folders containing possibly related files
    """
    ret: List[FileGroup] = []
    for group in groups:
        # folders containing only one or two files are not interesting
        if len(group.files) <= 2:
            continue
        ext = group.get_common_extension()
        common_files = [f for f in group.files if Path(f).suffix == ext]
        # folders containing only one or two files of the same type are not interesting
        if len(common_files) <= 2:
            continue

        ret.append(group)

    return ret


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
        semanic_weight = compute_semantic_weight(file, lines)
        return FileWeight(file, line_weights, semanic_weight)

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

# def compute_semantic_weight(file: Path, lines: List[str]):
#     constructs = load_lang_constructs(file)
#     return constructs.analyze(lines)