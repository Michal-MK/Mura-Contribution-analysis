import unittest
from pathlib import Path

from environment import TURTLE_GRAPHICS_REPO
from file_analyzer import compute_file_weight, has_weight_map
from lib import get_tracked_files

repos_path = "repositories"
single_commit = repos_path + "\\single_commit"

single_file = r'repositories\single_file\NasModel.cs'


class FileAnalyzerTest(unittest.TestCase):

    def test_get_tracked_files(self):
        file_weight = compute_file_weight(Path(single_file).absolute())
        print(file_weight.average_line_weight)
        print(file_weight.total_line_weight)
        print(file_weight.maximum_achievable_line_weight)


if __name__ == '__main__':
    unittest.main()
