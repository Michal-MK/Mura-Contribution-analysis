import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

from history_analyzer import FileSection

LANG_SEMANTICS_PATH = Path(__file__).parent / "lang-semantics"

SEMANTIC_ANALYZERS: Dict[str, 'LangSemantics'] = {}


class LangStructure:
    def __init__(self, kind: str, parent: Optional['LangStructure'], children: List['LangStructure']) -> None:
        self.kind = kind
        self.parent = parent
        self.children = children
        self.start = 0
        self.end = 0

    def in_range(self, start: int, end: int) -> bool:
        return self.start <= start and self.end >= end
    @property
    def weight(self) -> float:
        pass

    def __repr__(self):
        return f"LangStructure({self.kind}, [{self.start}-{self.end}])"

class LangSemantics:
    def __init__(self, lang_dir: Path, tool_executable: str):
        self.lang_dir = lang_dir
        self.tool = tool_executable

    def analyze(self, file: Path) -> float:
        args = [*self.tool.split(), str(self.lang_dir.parent / "declarations.json"), str(file)]
        process = subprocess.run(args, check=True, cwd=self.lang_dir, stdout=subprocess.PIPE, shell=True)
        output = process.stdout.decode("utf-8")
        lines = output.splitlines(keepends=True)
        structure = self._parse_structure(lines)
        return structure.weight

    def _parse_structure(self, lines: List[str]) -> LangStructure:
        root = parent = LangStructure('root', None, [])
        for line in lines:
            split = line.split('-', maxsplit=1)
            kind = split[0].strip()
            ranges = split[1].strip().replace('[', '').replace(']', '').split('-')
            start = int(ranges[0])
            end = int(ranges[1])
            if kind == 'class':
                _class = LangStructure(kind, parent, [])
                _class.start = start
                _class.end = end
                if parent.in_range(start, end):
                    parent.children.append(_class)
                else:
                    root.children.append(_class)
                    parent = _class
            if kind in ['function', 'property', 'field']:
                _def = LangStructure(kind, parent, [])
                _def.start = start
                _def.end = end
                if parent.in_range(start, end):
                    parent.children.append(_def)
                else:
                    root.children.append(_def)

        return root



def compute_semantic_weight(file: Path) -> float:
    semantics = load_semantic_parser(file)
    assert semantics is not None, f"No semantic parser for {file}"

    return semantics.analyze(file)


def has_semantic_parser(file: Path) -> bool:
    return load_semantic_parser(file) is not None


def load_semantic_parser(file: Path) -> Optional[LangSemantics]:
    extension = file.suffix.lstrip('.')

    if extension in SEMANTIC_ANALYZERS:
        return SEMANTIC_ANALYZERS[extension]

    lang_folder = LANG_SEMANTICS_PATH / extension
    if not lang_folder.exists():
        return None
    target_file = lang_folder / "target"
    executable = target_file.read_text(encoding="utf-8-sig")

    full_path = lang_folder.absolute()

    return LangSemantics(full_path, executable)
