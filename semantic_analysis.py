from pathlib import Path
from typing import List, Dict

from history_analyzer import FileSection


class LangConstruct:
    def __init__(self, parent: 'LangConstruct') -> None:
        self.parent = parent

class BlockConstruct(LangConstruct):
    def __init__(self, parent: LangConstruct, block_start: str, block_end: str) -> None:
        super().__init__(parent)
        self.block_start = block_start
        self.block_end = block_end

class LangSpec:
    def __init__(self):
        self.constructs: List[LangConstruct] = []
        self.is_object_oriented: bool

    def analyze(self, lines: List[str]) -> Dict[FileSection, float]:
        return {}

def load_lang_constructs(file: Path) -> LangSpec:
    ret = LangSpec()
