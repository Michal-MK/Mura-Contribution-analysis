'''
This file contains the PatternType for syntactic analysis.
'''
from enum import Enum


class PatternType(Enum):
    LITERAL = 1
    REGEX = 2