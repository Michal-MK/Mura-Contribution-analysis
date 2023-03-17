import json
import sys
import ast_comments  # type: ignore
from _ast import FunctionDef, ClassDef, Assign, Name, Attribute, Module, stmt, Expr, Constant
from pathlib import Path
from typing import Union
from libcst import parse_module


SUPPORTED_DECLARATIONS = ['class', 'function', 'property', 'field']

ASKED_DECLARATION = []

def read_token(token: Union[FunctionDef, ClassDef, Assign, Expr, stmt]) -> None:
    if isinstance(token, FunctionDef):
        if any(filter(lambda x: isinstance(x, Name) and x.id == 'property', token.decorator_list)):
            print(f"property - [{token.lineno}-{token.end_lineno}]")
        else:
            print(f"function - [{token.lineno}-{token.end_lineno}]")
        if token.name == "__init__":
            read_init_fields(token)
    if isinstance(token, Assign):
        unit = token.targets[0]
        if isinstance(unit, Attribute):
            print(f"field - [{unit.lineno}-{unit.end_lineno}]")
        elif isinstance(unit, Name):
            print(f"field - [{unit.lineno}-{unit.end_lineno}]")
    if isinstance(token, ClassDef):
        print(f"class - [{token.lineno}-{token.end_lineno}]")
        read_body(token)
    if isinstance(token, Expr):
        if isinstance(token.value, Constant):
            if isinstance(token.value.value, str):
                print(f"comment - [{token.lineno}-{token.end_lineno}]")
    if isinstance(token, ast_comments.Comment):
        print(f"comment - [{token.lineno}-{token.end_lineno}]")


def read_init_fields(init: FunctionDef) -> None:
    for token in init.body:
        if isinstance(token, Assign):
            unit = token.targets[0]
            if isinstance(unit, Attribute):
                print(f"field - [{unit.lineno}-{unit.end_lineno}]")
            elif isinstance(unit, Name):
                print(f"field - [{unit.lineno}-{unit.end_lineno}]")


def read_body(body_holder: Union[ClassDef, Module]) -> None:
    for token in body_holder.body:
        read_token(token)


def get_module(path: Path):
    with open(path, mode='r', encoding='utf-8-sig') as f:
        content = f.read()
    return ast_comments.parse(content)

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python3 ast_parser.py <path_to_declarations> <path_to_file>")
        exit(1)

    declaration_path = Path(args[0])
    script_path = Path(args[1])

    if not declaration_path.exists() or not script_path.exists():
        print("Invalid path in the arguments!")
        exit(1)

    with open(declaration_path.absolute(), mode='r') as f:
        global ASKED_DECLARATION
        ASKED_DECLARATION = json.load(f)

    module = get_module(script_path.absolute())
    read_body(module)

def main_debug():
    file = r"C:\Repositories\MetinSpeechToData\Python\bot_states\fight.py"
    file = r"simple.py"

    with open(file, mode='r', encoding='utf-8-sig') as f:
        content = f.read()
    module = parse_module(content)


DEBUG = False
if __name__ == '__main__':
    if DEBUG:
        main_debug()
    else:
        main()
