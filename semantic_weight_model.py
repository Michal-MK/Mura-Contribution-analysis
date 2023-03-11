from pathlib import Path
from typing import Dict

WEIGHT_MODELS: Dict[str, 'SemanticWeightModel'] = {}


class SemanticWeightModel:

    def __init__(self):
        self.property_field_lower_limit_multiplier: float = 0.0
        self.property_field_lower_limit: float = 0.0
        self.property_field_upper_limit_multiplier: float = 0.0
        self.property_field_upper_limit: float = 0.0
        self.function_lower_limit_multiplier: float = 0.0
        self.function_lower_limit: float = 0.0
        self.function_upper_limit_multiplier: float = 0.0
        self.function_upper_limit: float = 0.0
        self.class_upper_limit_multiplier: float = 0.0
        self.class_upper_limit: float = 0.0
        self.length_lower_limit_multiplier: float = 0.0
        self.length_lower_limit: float = 0.0
        self.length_upper_limit_multiplier: float = 0.0
        self.length_upper_limit: float = 0.0
        self.base_property_or_field_weight: float = 0.0
        self.base_function_weight: float = 0.0
        self.base_class_weight: float = 0.0
        self.base_length_weight: float = 0.0

    @property
    def average_base_weight(self) -> float:
        bases = list(filter(lambda x: x.startswith('base'), self.__dict__.keys()))
        base_values = map(lambda x: self.__dict__[x], bases)
        return sum(base_values) / len(bases)


    @staticmethod
    def _parse_file(weight_model: 'SemanticWeightModel', file: Path) -> 'SemanticWeightModel':
        with open(file) as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue

                trimmed = line.strip()
                split = trimmed.split('=')
                key = split[0].strip()
                value = float(split[1].strip())

                weight_model.__dict__[key] = value

        return weight_model

    @staticmethod
    def parse(file: Path) -> 'SemanticWeightModel':
        extension = file.suffix.lstrip('.')
        if extension in WEIGHT_MODELS:
            return WEIGHT_MODELS[extension]

        weight_model = SemanticWeightModel()
        base_weights = Path(__file__).parent / "lang-semantics" / "semantic_weights"

        weight_model = SemanticWeightModel._parse_file(weight_model, base_weights)

        specific_weights = base_weights.parent / extension / "semantic_weights"

        if specific_weights.exists():
            weight_model = SemanticWeightModel._parse_file(weight_model, specific_weights)

        WEIGHT_MODELS[extension] = weight_model
        return weight_model
