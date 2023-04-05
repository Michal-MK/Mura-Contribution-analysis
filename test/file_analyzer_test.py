import unittest
from pathlib import Path

import git

from file_analyzer import compute_syntactic_weight
from history_analyzer import CommitRange

repos_path = "../repositories"
single_commit = repos_path + "\\single_commit"
deletions = repos_path + "\\deletions"

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

    def test_deletions(self):
        repo = git.Repo(deletions)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        file = list(result.values())[0]

        content = file.history[1]

        self.assertTrue(file.line_count == 5)
        self.assertTrue(content[0].author == '')
        self.assertTrue(content[1].author == 'Michal-MK')
        self.assertTrue(content[2].author == 'Michal-MK')
        self.assertTrue(content[3].author == 'Michal-MK')
        self.assertTrue(content[4].author == 'Michal-MK')
        self.assertTrue(content[5].author == 'Michal-MK')
        self.assertTrue(len(content) == 6)

        self.assertTrue(file.changes[0].author == '')
        self.assertTrue(file.changes[1].author == 'Michal-MK')
        self.assertTrue(file.changes[2].author == 'Pepe')
        self.assertTrue(file.changes[3].author == 'Michal-MK')
        self.assertTrue(file.changes[4].author == 'Pepe')
        self.assertTrue(file.changes[5].author == 'Michal-MK')
        self.assertTrue(len(file.changes) == 6)


if __name__ == '__main__':
    unittest.main()
