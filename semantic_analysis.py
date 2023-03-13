import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from lib import FileGroup
from semantic_weight_model import SemanticWeightModel

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

    def compute_weight(self, weight_model: SemanticWeightModel) -> float:
        total_length_multiplier = 1.0
        class_count_multiplier = 1.0
        function_count_multiplier = 1.0
        property_or_field_count_multiplier = 1.0

        weight = 0.0
        base_length_weight = weight_model.base_length_weight
        base_class_weight = weight_model.base_class_weight
        base_function_weight = weight_model.base_function_weight
        base_property_or_field_weight = weight_model.base_property_or_field_weight

        if self.end > weight_model.length_upper_limit:
            total_length_multiplier = weight_model.length_upper_limit_multiplier
        elif self.end < weight_model.length_lower_limit:
            total_length_multiplier = weight_model.length_lower_limit_multiplier

        weight += base_length_weight * total_length_multiplier

        class_count = len(list(filter(lambda x: x.kind == 'class', self.children)))

        if class_count > weight_model.class_upper_limit:
            class_count_multiplier = weight_model.class_upper_limit_multiplier - 0.2 * (class_count - 1)

        weight += base_class_weight * class_count_multiplier

        function_count = len(list(filter(lambda x: x.kind == 'function', self.children)))

        if function_count > weight_model.function_upper_limit:
            function_count_multiplier = weight_model.function_upper_limit_multiplier - 0.05 * (function_count - 20)
        elif function_count < weight_model.function_lower_limit:
            function_count_multiplier = weight_model.function_lower_limit_multiplier - 0.1 * (4 - function_count)

        weight += base_function_weight * function_count_multiplier

        property_or_field_count = len(list(filter(lambda x: x.kind == 'property' or x.kind == 'field', self.children)))

        if property_or_field_count > weight_model.property_field_upper_limit:
            property_or_field_count_multiplier = weight_model.property_field_upper_limit_multiplier - 0.05 * (
                        property_or_field_count - 20)
        elif property_or_field_count < weight_model.property_field_lower_limit:
            property_or_field_count_multiplier = weight_model.property_field_lower_limit_multiplier - 0.05 * (
                        4 - property_or_field_count)

        weight += base_property_or_field_weight * property_or_field_count_multiplier

        return weight

    def __repr__(self):
        return f"LangStructure({self.kind}, [{self.start}-{self.end}])"


class LangSemantics:
    def __init__(self, lang_dir: Path, tool_executable: str):
        self.lang_dir = lang_dir
        self.tool = tool_executable

    def analyze(self, file: Path) -> Tuple[SemanticWeightModel, float]:
        args = [*self.tool.split(), str(self.lang_dir.parent / "declarations.json"), str(file)]
        process = subprocess.run(args, check=True, cwd=self.lang_dir, stdout=subprocess.PIPE, shell=True)
        output = process.stdout.decode("utf-8")
        lines = output.splitlines(keepends=True)
        structure = self._parse_structure(lines)
        model = SemanticWeightModel.parse(file)
        return model, structure.compute_weight(model)

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
                if root.end < end:
                    root.end = end
                if parent.in_range(start, end):
                    parent.children.append(_class)
                else:
                    root.children.append(_class)
                    parent = _class
            if kind in ['function', 'property', 'field']:
                _def = LangStructure(kind, parent, [])
                _def.start = start
                _def.end = end
                if root.end < end:
                    root.end = end
                if parent.in_range(start, end):
                    parent.children.append(_def)
                else:
                    root.children.append(_def)

        return root


def compute_semantic_weight(file: Path) -> Tuple[SemanticWeightModel, float]:
    semantics = load_semantic_parser(file)
    assert semantics is not None, f"No semantic parser for {file}"

    return semantics.analyze(file)


def compute_semantic_weight_grouped(file_group: FileGroup) -> List[Tuple[SemanticWeightModel, float]]:
    ret = []
    for file in file_group.files:
        abs_file = file.absolute()

        if has_semantic_parser(abs_file):
            sem_w = compute_semantic_weight(abs_file)
            ret.append(sem_w)
    return ret


def has_semantic_parser(file: Path) -> bool:
    return load_semantic_parser(file) is not None


def load_semantic_parser(file: Path) -> Optional[LangSemantics]:
    extension = file.suffix.lstrip('.')

    if not extension and file.name.startswith('.'):
        extension = file.name

    if not extension:
        # Now we reached files like "LICENCE" for which we have nothing
        return None

    if extension in SEMANTIC_ANALYZERS:
        return SEMANTIC_ANALYZERS[extension]

    lang_folder = LANG_SEMANTICS_PATH / extension
    if not lang_folder.exists():
        return None
    target_file = lang_folder / "target"
    executable = target_file.read_text(encoding="utf-8-sig")

    full_path = lang_folder.absolute()

    return LangSemantics(full_path, executable)
