import unittest
from pathlib import Path

import git

from file_analyzer import compute_syntactic_weight
from history_analyzer import CommitRange

repos_path = "../repositories"
single_commit = repos_path + "\\single_commit"
deletions = repos_path + "\\deletions"
randominsert = repos_path + "\\randominsertions"
empty = repos_path + "\\empty_file"
complex2 = repos_path + "\\complex2"
complex3 = repos_path + "\\complex3"
complex4 = repos_path + "\\complex4"
complex5 = repos_path + "\\complex5"
complex6 = repos_path + "\\complex6"

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
        self.assertTrue(content[0].author == 'Michal-MK')
        self.assertTrue(content[1].author == 'Michal-MK')
        self.assertTrue(content[2].author == 'Michal-MK')
        self.assertTrue(content[3].author == 'Michal-MK')
        self.assertTrue(content[4].author == 'Michal-MK')
        self.assertTrue(len(content) == 5)

        self.assertTrue(file.changes[0].author == 'Michal-MK')
        self.assertTrue(file.changes[1].author == 'Pepe')
        self.assertTrue(file.changes[2].author == 'Michal-MK')
        self.assertTrue(file.changes[3].author == 'Pepe')
        self.assertTrue(file.changes[4].author == 'Michal-MK')
        self.assertTrue(len(file.changes) == 5)

    def test_randominsert(self):
        repo = git.Repo(randominsert)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        file = list(result.values())[0]

        self.assertTrue(file.line_count == 13)
        self.assertTrue(len(file.changes) == 13)
        self.assertTrue(file.changes[0].author == 'Michal-MK')
        self.assertTrue(file.changes[0].content == 'Line 1\n')
        self.assertTrue(file.changes[4].author == 'Michal-MK')
        self.assertTrue(file.changes[4].content == 'Line 7\n')
        self.assertTrue(file.changes[5].author == 'Michal-MK')
        self.assertTrue(file.changes[5].content == 'Line 71\n')
        self.assertTrue(file.changes[9].author == 'Michal-MK')
        self.assertTrue(file.changes[9].content == 'Line 75\n')
        self.assertTrue(file.changes[10].author == 'Michal-MK')
        self.assertTrue(file.changes[10].content == 'Line 8\n')

    def test_complex2(self):
        repo = git.Repo(complex2)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        file = list(result.values())[0]

        self.assertTrue(file.line_count == 21)
        self.assertTrue(len(file.changes) == 21)
        self.assertTrue(file.changes[0].author == 'Michal-MK')
        self.assertTrue(file.changes[0].content == '1\n')
        self.assertTrue(file.changes[1].author == 'Michal-MK')
        self.assertTrue(file.changes[1].content == '2\n')
        self.assertTrue(file.changes[2].author == 'Michal-MK')
        self.assertTrue(file.changes[2].content == '3\n')
        self.assertTrue(file.changes[3].author == 'Michal-MK')
        self.assertTrue(file.changes[3].content == '4\n')
        self.assertTrue(file.changes[4].author == 'Random')
        self.assertTrue(file.changes[4].content == '51\n')
        self.assertTrue(file.changes[5].author == 'Random')
        self.assertTrue(file.changes[5].content == '61\n')
        self.assertTrue(file.changes[6].author == 'Michal-MK')
        self.assertTrue(file.changes[6].content == '7\n')
        self.assertTrue(file.changes[7].author == 'Michal-MK')
        self.assertTrue(file.changes[7].content == '8\n')
        self.assertTrue(file.changes[8].author == 'Michal-MK')
        self.assertTrue(file.changes[8].content == '9\n')
        self.assertTrue(file.changes[9].author == 'Michal-MK')
        self.assertTrue(file.changes[9].content == '10\n')
        self.assertTrue(file.changes[10].author == 'Michal-MK')
        self.assertTrue(file.changes[10].content == '15\n')
        self.assertTrue(file.changes[11].author == 'Michal-MK')
        self.assertTrue(file.changes[11].content == '16\n')
        self.assertTrue(file.changes[12].author == 'Michal-MK')
        self.assertTrue(file.changes[12].content == '17\n')
        self.assertTrue(file.changes[13].author == 'Michal-MK')
        self.assertTrue(file.changes[13].content == '18\n')
        self.assertTrue(file.changes[14].author == 'Random')
        self.assertTrue(file.changes[14].content == '181\n')
        self.assertTrue(file.changes[15].author == 'Random')
        self.assertTrue(file.changes[15].content == '182\n')
        self.assertTrue(file.changes[16].author == 'Random')
        self.assertTrue(file.changes[16].content == '183\n')
        self.assertTrue(file.changes[17].author == 'Random')
        self.assertTrue(file.changes[17].content == '184\n')
        self.assertTrue(file.changes[18].author == 'Michal-MK')
        self.assertTrue(file.changes[18].content == '19\n')
        self.assertTrue(file.changes[19].author == 'Michal-MK')
        self.assertTrue(file.changes[19].content == '20\n')
        self.assertTrue(file.changes[20].author == 'Michal-MK')
        self.assertTrue(file.changes[20].content == '')

    def test_empty(self):
        repo = git.Repo(empty)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        file = list(result.values())[0]

        self.assertTrue(file.line_count == -1)
        self.assertTrue(len(file.changes) == 1)
        self.assertTrue(file.changes[0].author == 'Michal-MK')

    def test_complex3(self):
        repo = git.Repo(complex3)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        file = list(result.values())[0]

        self.assertTrue(file.changes[0].author == 'Michal-MK')
        self.assertTrue(file.changes[0].content == '1\n')
        self.assertTrue(file.changes[1].author == 'Michal-MK')
        self.assertTrue(file.changes[1].content == '2\n')
        self.assertTrue(file.changes[2].author == 'Pepe')
        self.assertTrue(file.changes[2].content == '31\n')
        self.assertTrue(file.changes[3].author == 'Michal-MK')
        self.assertTrue(file.changes[3].content == '4\n')
        self.assertTrue(file.changes[4].author == 'Michal-MK')
        self.assertTrue(file.changes[4].content == '5\n')
        self.assertTrue(file.changes[5].author == 'Michal-MK')
        self.assertTrue(file.changes[5].content == '\n')
        self.assertTrue(file.changes[6].author == 'Pepe')
        self.assertTrue(file.changes[6].content == '\n')
        self.assertTrue(file.changes[7].author == 'Michal-MK')
        self.assertTrue(file.changes[7].content == '6\n')
        self.assertTrue(file.changes[8].author == 'Michal-MK')
        self.assertTrue(file.changes[8].content == '7\n')
        self.assertTrue(file.changes[9].author == 'Michal-MK')
        self.assertTrue(file.changes[9].content == '8\n')

    def test_complex4(self):
        repo = git.Repo(complex4)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        file = list(result.values())[0]

        self.assertTrue(file.changes[0].author == 'Michal-MK')
        self.assertTrue(file.changes[0].content == 'A\n')
        self.assertTrue(file.changes[1].author == 'Michal-MK')
        self.assertTrue(file.changes[1].content == 'B\n')
        self.assertTrue(file.changes[2].author == 'Michal-MK')
        self.assertTrue(file.changes[2].content == 'C\n')
        self.assertTrue(file.changes[3].author == 'Pepe')
        self.assertTrue(file.changes[3].content == '1\n')
        self.assertTrue(file.changes[4].author == 'Pepe')
        self.assertTrue(file.changes[4].content == '2\n')
        self.assertTrue(file.changes[5].author == 'Michal-MK')
        self.assertTrue(file.changes[5].content == 'D\n')
        self.assertTrue(file.changes[6].author == 'Michal-MK')
        self.assertTrue(file.changes[6].content == 'E\n')
        self.assertTrue(file.changes[7].author == 'Michal-MK')
        self.assertTrue(file.changes[7].content == 'F')

    def test_complex5(self):
        repo = git.Repo(complex5)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        file = list(result.values())[0]

        self.assertTrue(file.changes[8].author == 'Michal-MK')
        self.assertTrue(file.changes[8].content == '\n')
        self.assertTrue(file.changes[9].author == 'Michal-MK')
        self.assertTrue(file.changes[9].content == 'import static org.hamcrest.Matchers.hasSize;\n')
        self.assertTrue(file.changes[35].author == 'Michal-MK')
        self.assertTrue(file.changes[35].content == '                .lecturerId(61L)\n')
        self.assertTrue(file.changes[36].author == 'Michal-MK')
        self.assertTrue(file.changes[36].content == '                .courseId(10L)\n')
        self.assertTrue(file.changes[86].author == 'Michal-MK')
        self.assertTrue(file.changes[86].content == '        for (int i = 3; i < 7; i++) {\n')
        self.assertTrue(file.changes[99].author == 'Michal-MK')
        self.assertTrue(file.changes[99].content == '}')


    def test_complex6(self):
            repo = git.Repo(complex6)
            c_range = CommitRange(repo, 'HEAD', 'ROOT')
            result = c_range.analyze()

            file = list(result.values())[0]

            pass



if __name__ == '__main__':
    unittest.main()
