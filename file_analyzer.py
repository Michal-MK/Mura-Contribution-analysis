import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from configuration import Configuration
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
