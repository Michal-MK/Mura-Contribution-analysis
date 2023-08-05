from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from lib import Contributor
from uni_chars import CONTRIBUTOR


def calculate_ownership(tree, ownership_cache=None) -> Dict[Contributor, float]:
    if ownership_cache is None:
        ownership_cache = {}
    if all(isinstance(value, float) for value in tree.values()):
        return tree
    ownership: Dict[Contributor, float] = defaultdict(float)
    count = 0
    for value in tree.values():
        if isinstance(value, dict):
            sub_ownership = calculate_ownership(value, ownership_cache)
            for owner, percentage_value in sub_ownership.items():
                ownership[owner] += percentage_value
            count += 1
    for owner in ownership:
        ownership[owner] /= count
    ownership_cache[id(tree)] = ownership
    return ownership


def build_tree(triples: List[Tuple[Path, float, Contributor]]) -> Dict[Any, Any]:
    tree: Dict[Any, Any] = {}
    for triple in triples:
        current = tree
        for path_segment in triple[0].parts:
            if path_segment not in current:
                current[path_segment] = {}
            current = current[path_segment]
        current[triple[2]] = current.get(triple[2], 0) + triple[1]
    return tree


def print_tree(tree: Dict[Any, Any], level=0, prefix='', ownership_cache: Optional[Dict[Contributor, float]] = None) \
        -> None:
    '''
    Prints a tree structure of the repository
    '''
    if ownership_cache is None:
        ownership_cache = {}
    for i, (name, value) in enumerate(tree.items()):
        if i == len(tree) - 1:
            connector = '└── '
            new_prefix = prefix + '    '
        else:
            connector = '├── '
            new_prefix = prefix + '│   '
        if isinstance(value, dict):
            if all(isinstance(v, float) for v in value.values()):
                owners_str = ', '.join(
                    [f'{owner.name}: {value * 100:.0f}%' for owner, value in value.items() if owner.name != '?'])
                print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
            else:
                sub_ownerships = [calculate_ownership(v, ownership_cache) for v in value.values() if
                                  isinstance(v, dict)]
                if len(sub_ownerships) > 0 \
                        and all(sub_ownerships[0] == sub_ownership for sub_ownership in sub_ownerships):
                    print(f'{prefix}{connector}{name}')
                else:
                    owners_str = ', '.join([f'{owner.name}: {value * 100:.0f}%' for owner, value in
                                            calculate_ownership(value, ownership_cache).items() if owner.name != '?'])
                    print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
                print_tree(value, level + 1, new_prefix, ownership_cache)
