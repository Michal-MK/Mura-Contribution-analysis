import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

from history_analyzer import FileSection

LANG_SEMANTICS_PATH = Path(__file__).parent / "lang-semantics"

SEMANTIC_ANALYZERS: Dict[str, 'LangSemantics'] = {}


class LangSemantics:
    def __init__(self, lang_dir: Path, tool_executable: str):
        self.lang_dir = lang_dir
        self.tool = tool_executable

    def analyze(self, file: Path) -> Dict[FileSection, float]:
        args = [*self.tool.split(), str(self.lang_dir.parent / "declarations.json"), str(file)]
        print(f"Analyzing {file} with command: {args} in {self.lang_dir}")
        process = subprocess.run(args, check=True, cwd=self.lang_dir, stdout=subprocess.PIPE, shell=True)
        output = process.stdout.decode("utf-8")
        lines = output.splitlines()
        print(lines)
        return {}


def compute_semantic_weight(file: Path) -> Dict[FileSection, float]:
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
