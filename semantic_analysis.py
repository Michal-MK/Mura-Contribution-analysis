import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from history_analyzer import FileSection

loaded_semantics: Dict[str, 'LangSpec'] = {}


class LangConstruct:
    def __init__(self, parent: Optional['LangConstruct'] = None) -> None:
        self.parent = parent


class LineConstruct(LangConstruct):
    def __init__(self, line: str, parent: Optional[LangConstruct] = None) -> None:
        super().__init__(parent)
        self.line = re.compile(line)


class BlockConstruct(LangConstruct):
    def __init__(self, block_start: str, block_end: str, parent: Optional[LangConstruct] = None) -> None:
        super().__init__(parent)
        self.block_start = re.compile(block_start)
        self.block_end = re.compile(block_end)


class LangSpec:
    def __init__(self):
        self.constructs: List[LangConstruct] = []
        self.is_object_oriented: bool

    def load(self, file):
        semantics: Dict[str, Any] = json.load(file)
        CLASS = "block_class_construct"
        FUNCTION = "block_function_construct"
        VARIABLE = 'variable_construct'
        PROPERTY = 'property_construct'

        for section in [CLASS, FUNCTION, VARIABLE, PROPERTY]:
            if section not in semantics:
                continue
            data = semantics[section]
            if section in [CLASS, FUNCTION]:
                self.constructs.append(BlockConstruct(data["start_identifier"], data["end_identifier"]))
            elif section == PROPERTY:
                self.constructs.append(LineConstruct(data["identifier"]))
            elif section == VARIABLE:
                self.constructs.append(LineConstruct(data["identifier"]))

    def analyze(self, lines: List[str]) -> Dict[FileSection, float]:
        ret : Dict[FileSection, float] = {}

        line_no = 0
        for line in lines:
            for construct in self.constructs:
                if isinstance(construct, LineConstruct):
                    if construct.line.match(line):
                        ret[FileSection(line_no, 1, 0, 0, "-")] = 1
                        break
                elif isinstance(construct, BlockConstruct):
                    if construct.block_start.match(line):
                        ret[FileSection(line_no, 1, 0, 0, "-")] = 1
                        break
            line_no += 1

        return ret

def compute_semantic_weight(file: Path, lines: List[str]) -> Dict[FileSection, float]:
    constructs = load_lang_constructs(file)
    return constructs.analyze(lines)

def has_semantics(file: Path) -> bool:
    if file.is_dir():
        return False
    suffix = file.suffix.lstrip('.')
    return os.path.isfile(os.path.join(Path(__file__).parent, "lang-specs", suffix + ".json"))


def load_lang_constructs(file_path: Path) -> LangSpec:
    """
    Load the semantics of a file
    :param file_path: The file to load the weight map for
    :return: The weight map
    """
    suffix = file_path.suffix.lstrip('.')
    if suffix not in loaded_semantics:
        ret = LangSpec()
        with open(os.path.join(Path(__file__).parent, "lang-specs", suffix + ".json"), 'r') as f:
            ret.load(f)
            loaded_semantics[suffix] = ret
        return ret
    else:
        return loaded_semantics[suffix]
