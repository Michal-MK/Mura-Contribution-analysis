import os
from typing import List, Dict
from pathlib import Path

from semantic_analysis import compute_semantic_weight
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
    def __init__(self, file: Path, line_weights: List[float], weight_model: SemanticWeightModel,
                 semantic_weight: float):
        self.file = file
        self.line_weights = line_weights
        self.weight_model = weight_model
        self.semantic_weight = semantic_weight

    @property
    def total_line_weight(self):
        return sum(self.line_weights)

    @property
    def syntactic_weight(self):
        return self.average_line_weight * self.weight_model.average_base_weight

    @property
    def final_weight(self):
        return self.syntactic_weight + self.semantic_weight

    @property
    def average_line_weight(self):
        return self.total_line_weight / len(self.line_weights)

    @property
    def maximum_achievable_line_weight(self):
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
        model, semantic_weight = compute_semantic_weight(file)
        return FileWeight(file, line_weights, model, semantic_weight)


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
