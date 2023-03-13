from typing import Tuple, List

from history_analyzer import AnalysisResult
from lib import FileGroup
from semantic_weight_model import SemanticWeightModel


def merge_results(syntax: AnalysisResult,
                  racked_files: List[FileGroup],
                  semantics: List[List[Tuple[SemanticWeightModel, float]]]) -> None:
    for key, value in syntax.items():
        print(f"{key} - {value}")

