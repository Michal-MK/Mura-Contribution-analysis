from pathlib import Path
from typing import Any


def parse_model_content(model: Any, file: Path) -> Any:
    with open(file) as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue

            trimmed = line.strip()
            split = trimmed.split('=')
            key = split[0].strip()
            value = float(split[1].strip())

            model.__dict__[key] = value

    return model