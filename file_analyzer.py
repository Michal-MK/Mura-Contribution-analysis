import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from configuration import Configuration
from history_analyzer import Ownership
from lib import FileGroup
from semantic_analysis import LangElement
from semantic_weight_model import SemanticWeightModel
from syntactic_weight_model import SyntacticWeightModel

loaded_weight_maps: Dict[str, 'SyntacticWeightModel'] = {}


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
    def __init__(self, file: Path, file_weight: float, individual_line_weights: List[float]):
        self.file = file
        self.file_weight = file_weight
        self.line_weights = individual_line_weights
        self.weight_model: Optional[SemanticWeightModel] = None
        self.semantic_structure: Optional[LangElement] = None

    @property
    def total_line_weight(self):
        return sum(self.line_weights)

    @property
    def syntactic_weight(self):
        return self.file_weight

    @property
    def final_weight(self) -> float:
        assert self.semantic_weight is not None, "Semantic weight was not assigned yet! Cannot compute final_weight!"
        return self.syntactic_weight + self.semantic_weight

    @property
    def semantic_weight(self):
        assert self.weight_model is not None, "weight_model was not assigned yet! Cannot compute semantic_weight!"
        return self.semantic_structure.compute_weight(self.weight_model)

    @property
    def average_line_weight(self):
        return self.total_line_weight / self.num_lines

    @property
    def num_lines(self):
        return len(self.line_weights)


def load_weight_map(file_path: Path) -> SyntacticWeightModel:
    """
    Load the weight map for a file
    :param file_path: The file to load the weight map for
    :return: The weight map
    """
    suffix = file_path.suffix.lstrip('.')
    if suffix not in loaded_weight_maps:
        ret = SyntacticWeightModel()
        with open(os.path.join(Path(__file__).parent, "lang-syntax", suffix + ".literal.txt"), 'r') as f:
            ret.load_literals(f)
        with open(os.path.join(Path(__file__).parent, "lang-syntax", suffix + ".regex.txt"), 'r') as f:
            ret.load_regex(f)
        loaded_weight_maps[suffix] = ret
        return ret
    else:
        return loaded_weight_maps[suffix]


def has_weight_map(file: Path) -> bool:
    if file.is_dir():
        return False
    suffix = file.suffix.lstrip('.')
    return os.path.isfile(os.path.join(Path(__file__).parent, "lang-syntax", suffix + ".json"))


def compute_syntactic_weight(file: Path, config: Configuration) -> Optional[FileWeight]:
    """
    Compute the weight of a file
    :param file: full path to the file
    :return: The weight of the file based on its contents
    """
    try:
        with open(file, 'r', encoding='UTF-8-SIG') as f:
            lines = f.readlines()
            file_weight, line_weights = compute_file_weight(file, lines, config)
            return FileWeight(file, file_weight, line_weights)
    except Exception:
        return None


def compute_lines_weight(file: Path, lines: List[str], config: Configuration) -> List[float]:
    strip_chars = ' \t\r\n'
    weight_map = load_weight_map(file)
    blank_line_handler = BlankLineHandler()
    ret = []
    for line in lines:
        line_stripped = line.strip(strip_chars)
        if line_stripped == '':
            ret.append(blank_line_handler.next())
            continue
        blank_line_handler.clear()
        if len(line) >= config.max_line_length:
            ret.append(config.over_max_line_length_weight)
        weight = weight_map.get_weight(line, line_stripped)
        ret.append(weight)
    return ret


def compute_file_weight(file: Path, lines: List[str], config: Configuration) -> Tuple[float, List[float]]:
    line_weights = compute_lines_weight(file, lines, config)
    weight_sum = sum(line_weights)
    ratio = weight_sum / len(line_weights)
    return config.single_file_weight * ratio, line_weights


def get_complete_files(ownerships: Dict[Path, Ownership], threshold: float) -> Dict[Path, datetime]:
    complete_files: Dict[Path, datetime] = {}
    for path, ownership in ownerships.items():
        prev_size = None
        complete_date = None
        history_len = len(ownership.history.values())
        if history_len == 1:
            complete_date = next(iter(ownership.history.values())).content[0].change_date
        else:
            for history in ownership.history.values():
                size = sum(len(line.content) for line in history.content)
                if prev_size is not None and prev_size > 0:
                    if abs(size - prev_size) / prev_size > threshold:
                        complete_date = None
                    elif complete_date is None:
                        complete_date = history.content[0].change_date
                prev_size = size
            if prev_size and prev_size <= 0 and complete_date is None:
                complete_date = next(iter(ownership.history.values())).content[0].change_date
                # Probably a binary file
        if complete_date is not None:
            complete_files[path] = complete_date
    return complete_files


def group_by_common_suffix(paths: List[Path]) -> Dict[str, List[Path]]:
    result = defaultdict(list)
    for path1 in paths:
        stem1 = path1.stem
        max_common_suffix = ''
        for path2 in paths:
            if path1 == path2:
                continue
            stem2 = path2.stem
            min_len = min(len(stem1), len(stem2))
            common_suffix = ''
            for i in range(min_len):
                char = stem1[-i-1]
                if stem2[-i-1] == char:
                    common_suffix = char + common_suffix
                else:
                    break
            if len(common_suffix) > len(max_common_suffix):
                max_common_suffix = common_suffix
        result[max_common_suffix].append(path1)
    return dict(result)

def convert_file_groups(file_groups: List[FileGroup]) -> List[Path]:
    result = []
    for file_group in file_groups:
        result.extend(file_group.files)
    return result


def assign_scores(file_groups: List[FileGroup], history_analysis: Dict[Path, Ownership], config: Configuration) \
        -> Dict[Path, float]:
    def sort_key(path: Path) -> datetime:
        ret = complete_files.get(path, None)
        if ret is not None:
            if ret.tzinfo is None or ret.tzinfo.utcoffset(ret) is None:
                ret = ret.replace(tzinfo=timezone.utc)
            return ret
        return datetime.now().astimezone()

    groups = convert_file_groups(file_groups)
    grouped_files = group_by_common_suffix(groups)
    complete_files = get_complete_files(history_analysis, config.complete_file_threshold)
    for path, date in complete_files.items():
        if date.tzinfo is None or date.tzinfo.utcoffset(date) is None:
            complete_files[path] = date.replace(tzinfo=timezone.utc)
    result = {}
    for suffix, paths in grouped_files.items():
        try:
            sorted_paths = sorted(paths, key=sort_key)
        except Exception as e:
            pls = []
            for path in paths:
                pls.append(sort_key(path))
            pass
        current_first_relevant_occurrence = sort_key(sorted_paths[0])
        existing_files = 0
        increase_past_dates = []
        relevant_occurrences = []

        for i, path in enumerate(sorted_paths):
            # handle self
            if current_first_relevant_occurrence == sort_key(path):
                result[path] = 1.0
                increase_past_dates.append(current_first_relevant_occurrence + timedelta(days=config.num_days_grace_period))
                relevant_occurrences.append(current_first_relevant_occurrence)
                continue

            other_file_completion_date = sort_key(path)

            while increase_past_dates and other_file_completion_date > increase_past_dates[0]:
                increase_past_dates.pop(0)
                current_first_relevant_occurrence = relevant_occurrences.pop(0)
                existing_files += 1

            increase = 0

            if other_file_completion_date - timedelta(days=config.num_days_grace_period) \
                > current_first_relevant_occurrence:
                current_first_relevant_occurrence = other_file_completion_date
                increase_past_dates.append(current_first_relevant_occurrence + timedelta(days=config.num_days_grace_period))
                relevant_occurrences.append(current_first_relevant_occurrence)
            else:
                increase_past_dates.append(current_first_relevant_occurrence + timedelta(days=config.num_days_grace_period))
                relevant_occurrences.append(other_file_completion_date)


            score = max(1 - existing_files * 0.1, 0.5)

            existing_files += increase
            result[path] = score
    return result
