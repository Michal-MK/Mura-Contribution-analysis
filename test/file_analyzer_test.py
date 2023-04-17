import unittest
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict

import git

from configuration import Configuration
from file_analyzer import assign_scores, group_by_common_suffix, convert_file_groups
from history_analyzer import CommitRange, Ownership
from lib import FileGroup

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

    def test_deletions(self):
        repo = git.Repo(deletions)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        file = list(result.values())[0]

        content = file.history['cd342dba8fe190e9cc645334b8793612ed1bbc38']

        self.assertTrue(file.line_count == 5)
        self.assertTrue(content.content[0].author == 'Michal-MK')
        self.assertTrue(content.content[1].author == 'Michal-MK')
        self.assertTrue(content.content[2].author == 'Michal-MK')
        self.assertTrue(content.content[3].author == 'Michal-MK')
        self.assertTrue(content.content[4].author == 'Michal-MK')
        self.assertTrue(len(content.content) == 5)

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

    def setUp(self) -> None:
        self.groups = [
            FileGroup('',
                      [Path('AController.txt'), Path('BController.txt'), Path('CController.txt'), Path('DModel.txt'),
                       Path('EModel.txt')])
        ]

        conv = convert_file_groups(self.groups)
        res = group_by_common_suffix(conv)

        grouped_files = {
            'Controller': [Path('AController.txt'), Path('BController.txt'), Path('CController.txt')],
            'Model': [Path('DModel.txt'), Path('EModel.txt')]
        }

        self.assertTrue(res == grouped_files)

    def test_assign_scores_no_grace(self):
        expected_result = {
            Path('AController.txt'): 1.0,
            Path('BController.txt'): 0.9,
            Path('CController.txt'): 0.8,
            Path('DModel.txt'): 1.0,
            Path('EModel.txt'): 0.9
        }

        config = Configuration()
        config.num_days_grace_period = 0

        analysis: Dict[Path, Ownership] = {
            Path('AController.txt'):
                Ownership(Path('AController.txt'), 1, '\n' * 20, datetime(2022, 1, 1), uuid.uuid1().hex, 'Michal-MK'),
            Path('BController.txt'):
                Ownership(Path('BController.txt'), 1, '\n' * 20, datetime(2022, 1, 2), uuid.uuid1().hex, 'Michal-MK'),
            Path('CController.txt'):
                Ownership(Path('CController.txt'), 1, '\n' * 20, datetime(2022, 1, 3), uuid.uuid1().hex, 'Michal-MK'),
            Path('DModel.txt'):
                Ownership(Path('DModel.txt'), 1, '\n' * 20, datetime(2022, 1, 4), uuid.uuid1().hex, 'Michal-MK'),
            Path('EModel.txt'):
                Ownership(Path('EModel.txt'), 1, '\n' * 20, datetime(2022, 1, 5), uuid.uuid1().hex, 'Michal-MK')
        }

        result = assign_scores(self.groups, analysis, config)
        self.assertTrue(result == expected_result, f'Expected {expected_result}, but got {result}')

    def test_assign_scores_7_days(self):
            expected_result = {
                Path('AController.txt'): 1.0,
                Path('BController.txt'): 1.0,
                Path('CController.txt'): 0.8,
                Path('DModel.txt'): 1.0,
                Path('EModel.txt'): 0.9
            }

            config = Configuration()
            config.num_days_grace_period = 7

            analysis: Dict[Path, Ownership] = {
                Path('AController.txt'):
                    Ownership(Path('AController.txt'), 1, '\n' * 20, datetime(2022, 1, 1), uuid.uuid1().hex, 'Michal-MK'),
                Path('BController.txt'):
                    Ownership(Path('BController.txt'), 1, '\n' * 20, datetime(2022, 1, 6), uuid.uuid1().hex, 'Michal-MK'),
                Path('CController.txt'):
                    Ownership(Path('CController.txt'), 1, '\n' * 20, datetime(2022, 1, 20), uuid.uuid1().hex, 'Michal-MK'),
                Path('DModel.txt'):
                    Ownership(Path('DModel.txt'), 1, '\n' * 20, datetime(2022, 1, 4), uuid.uuid1().hex, 'Michal-MK'),
                Path('EModel.txt'):
                    Ownership(Path('EModel.txt'), 1, '\n' * 20, datetime(2022, 1, 20), uuid.uuid1().hex, 'Michal-MK')
            }

            result = assign_scores(self.groups, analysis, config)
            self.assertTrue(result == expected_result, f'Expected {expected_result}, but got {result}')

    def test_assign_scores_7_days_complex(self):
            expected_result = {
                Path('AController.txt'): 1.0,
                Path('BController.txt'): 1.0,
                Path('CController.txt'): 0.8,
                Path('QController.txt'): 0.7,
                Path('DModel.txt'): 1.0,
                Path('EModel.txt'): 0.9,
                Path('FModel.txt'): 0.9
            }

            self.groups[0].files.append(Path('QController.txt'))
            self.groups[0].files.append(Path('FModel.txt'))

            config = Configuration()
            config.num_days_grace_period = 7

            analysis: Dict[Path, Ownership] = {
                Path('AController.txt'):
                    Ownership(Path('AController.txt'), 1, '\n' * 20, datetime(2022, 1, 1), uuid.uuid1().hex, 'Michal-MK'),
                Path('BController.txt'):
                    Ownership(Path('BController.txt'), 1, '\n' * 20, datetime(2022, 1, 6), uuid.uuid1().hex, 'Michal-MK'),
                Path('CController.txt'):
                    Ownership(Path('CController.txt'), 1, '\n' * 20, datetime(2022, 1, 20), uuid.uuid1().hex, 'Michal-MK'),
                Path('QController.txt'):
                    Ownership(Path('CController.txt'), 1, '\n' * 20, datetime(2022, 1, 28), uuid.uuid1().hex, 'Michal-MK'),
                Path('DModel.txt'):
                    Ownership(Path('DModel.txt'), 1, '\n' * 20, datetime(2022, 1, 4), uuid.uuid1().hex, 'Michal-MK'),
                Path('EModel.txt'):
                    Ownership(Path('EModel.txt'), 1, '\n' * 20, datetime(2022, 1, 20), uuid.uuid1().hex, 'Michal-MK'),
                Path('FModel.txt'):
                    Ownership(Path('EModel.txt'), 1, '\n' * 20, datetime(2022, 1, 22), uuid.uuid1().hex, 'Michal-MK')
            }

            result = assign_scores(self.groups, analysis, config)
            self.assertTrue(result == expected_result, f'Expected {expected_result}, but got {result}')


if __name__ == '__main__':
    unittest.main()
