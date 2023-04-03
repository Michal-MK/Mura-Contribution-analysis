import unittest
from pathlib import Path

from file_analyzer import compute_syntactic_weight

repos_path = "../repositories"
single_commit = repos_path + "\\single_commit"

single_file = r'../repositories/single_file/NasModel.cs'


class FileAnalyzerTest(unittest.TestCase):

    def test_file_weight_single_file(self):
        file_weight = compute_syntactic_weight(Path(single_file).absolute())
        print(file_weight.average_line_weight)
        print(file_weight.total_line_weight)
        print(file_weight.maximum_achievable_line_weight)
        #print(file_weight.semantic_weight)
        #print(file_weight.syntactic_weight)
        #print(file_weight.final_weight)


if __name__ == '__main__':
    unittest.main()
