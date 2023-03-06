import unittest
from pathlib import Path

from environment import TURTLE_GRAPHICS_REPO
from lib import get_tracked_files
from semantic_analysis import compute_semantic_weight


class SemanticsAnalyzerTest(unittest.TestCase):

    def test_semantic_weight_tg(self):
        weights = []
        file_groups = get_tracked_files(Path(TURTLE_GRAPHICS_REPO))
        for group in file_groups:
            for file in group.files:
                print(file)
                if file.suffix == ".cs":
                    sem_w = compute_semantic_weight(file, file.read_text().splitlines(keepends=True))
                    weights.append(sem_w)
        pass
if __name__ == '__main__':
    unittest.main()