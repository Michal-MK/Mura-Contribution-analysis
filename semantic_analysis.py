import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Iterator

from configuration import Configuration
from lib import FileGroup
from semantic_weight_model import SemanticWeightModel
from uni_chars import *

LANG_SEMANTICS_PATH = Path(__file__).parent / "lang-semantics"

SEMANTIC_ANALYZERS: Dict[str, 'LangSemantics'] = {}


class LangElement:
    def __init__(self, kind: str, parent: Optional['LangElement'], children: List['LangElement']) -> None:
        self.kind = kind
        self.parent = parent
        self.children = children
        self.start = 0
        self.end = 0

    def iterate(self) -> Iterator['LangElement']:
        yield self
        for child in self.children:
            yield from child.iterate()

    @property
    def classes(self) -> Iterator['LangElement']:
        return filter(lambda x: x.kind == "class", [self, *self.children])

    @property
    def functions(self) -> Iterator['LangElement']:
        return filter(lambda x: x.kind == "function", self.children)

    @property
    def fields(self) -> Iterator['LangElement']:
        return filter(lambda x: x.kind == "field", self.children)

    @property
    def properties(self) -> Iterator['LangElement']:
        return filter(lambda x: x.kind == "property", self.children)

    @property
    def comments(self) -> Iterator['LangElement']:
        return filter(lambda x: x.kind == "comment", self.children)

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

        class_count = len(list(self.classes))

        if class_count > weight_model.class_upper_limit:
            class_count_multiplier = weight_model.class_upper_limit_multiplier - 0.2 * (class_count - 1)

        weight += base_class_weight * class_count_multiplier

        function_count = len(list(self.functions))

        if function_count > weight_model.function_upper_limit:
            function_count_multiplier = weight_model.function_upper_limit_multiplier - 0.05 * (function_count - 20)
        elif function_count < weight_model.function_lower_limit:
            function_count_multiplier = weight_model.function_lower_limit_multiplier - 0.1 * (4 - function_count)

        weight += base_function_weight * function_count_multiplier

        property_or_field_count = len(list(self.fields) + list(self.properties))

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

    def analyze(self, files: List[Path]) -> List[Tuple[Path, SemanticWeightModel, LangElement]]:
        results: List[Tuple[Path, SemanticWeightModel, LangElement]] = []

        file_names = [str(file) for file in files]
        args = [*self.tool.split(), str(self.lang_dir.parent / "declarations.json"), *file_names]
        process = subprocess.run(args, check=True, cwd=self.lang_dir, stdout=subprocess.PIPE, shell=True)
        output = process.stdout.decode("utf-8")
        lines = output.splitlines(keepends=True)
        file_sections: List[Tuple[Path, List[str]]] = []

        file_section: Optional[Tuple[Path, List[str]]] = None
        for line in lines:
            if line.strip() in file_names:
                if file_section:
                    file_sections.append(file_section)
                file_section = (Path(line.strip()), [])
                continue
            assert file_section is not None, "File section should be initialized, as the first line is a file name!"
            file_section[1].append(line)

        assert file_section is not None, "File section should be initialized, as the first line is a file name!"
        file_sections.append(file_section)  # Append the last file section

        for file_section in file_sections:
            structure = self._parse_structure(file_section[1])
            model = SemanticWeightModel.parse(
                file_section[0])  # This is safe as the loop is executed only if there are files
            results.append((file_section[0], model, structure))

        return results

    def _parse_structure(self, lines: List[str]) -> LangElement:
        root = parent = LangElement('root', None, [])
        for line in lines:
            split = line.split('-', maxsplit=1)
            kind = split[0].strip()
            ranges = split[1].strip().replace('[', '').replace(']', '').split('-')
            start = int(ranges[0])
            end = int(ranges[1])
            elem = LangElement(kind, parent, [])
            elem.start = start
            elem.end = end
            if root.end < end:
                root.end = end
            if parent.in_range(start, end):
                parent.children.append(elem)
            else:
                root.children.append(elem)
                if kind == 'class':
                    parent = elem
        return root


def compute_semantic_weight(file: Path) -> Tuple[Path, SemanticWeightModel, 'LangElement']:
    semantics = load_semantic_parser(file)
    assert semantics is not None, f"No semantic parser for {file}"

    return semantics.analyze([file])[0]


def compute_semantic_weight_grouped(config: Configuration, file_group: FileGroup) -> List[Tuple[Path, SemanticWeightModel, 'LangElement']]:
    files = [file.absolute() for file in file_group.files]

    files_by_extension: Dict[str, List[Path]] = {}
    for file in files:
        if file.suffix not in files_by_extension:
            files_by_extension[file.suffix] = []
        files_by_extension[file.suffix].append(file)

    unsorted_ret: List[Tuple[Path, SemanticWeightModel, 'LangElement']] = []

    for ext, files in files_by_extension.items():
        semantics = load_semantic_parser(files[0])
        if semantics is None or ext in config.ignored_extensions:
            for file in files:
                unsorted_ret.append((file, SemanticWeightModel(), LangElement('root', None, [])))
        else:
            unsorted_ret.extend(semantics.analyze(files))

    unsorted_ret.sort(key=lambda x: file_group.files.index(x[0]))

    return unsorted_ret


def compute_semantic_weight_result(config: Configuration, file_groups: List[FileGroup], verbose=False) \
        -> List[List[Tuple[Path, SemanticWeightModel, 'LangElement']]]:
    total_groups = len(file_groups)
    counter = 1
    start = time.time()
    ret = []
    for group in file_groups:
        grouped_semantic_weight = compute_semantic_weight_grouped(config, group)
        ret.append(grouped_semantic_weight)
        progress = time.time()
        if verbose:
            print(f"{INFO} Semantic analysis: {progress - start:.2f}s => {counter}/{total_groups}")
            counter += 1

    if verbose:
        print(f"{SUCCESS} Semantic analysis DONE")
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

    semantics = LangSemantics(full_path, executable)
    SEMANTIC_ANALYZERS[extension] = semantics
    return semantics
