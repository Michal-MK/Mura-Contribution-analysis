import datetime
import unittest
from math import isclose
from pathlib import Path
from typing import List

import git

import lib
from environment_local import TURTLE_GRAPHICS_REPO
from history_analyzer import get_file_changes, AuthorName, CommitRange, calculate_percentage, LineMetadata

TEST_REPO2 = Path("..\\repositories\\single_file")
TEST_REPO_UNMERGED = Path("..\\repositories\\unmerged")
TEST_REPO_UNMERGED_MULTIPLE = Path("..\\repositories\\unmerged_multiple")


def by(section: List[LineMetadata], author: AuthorName):
    return all(filter(lambda x: x == author, map(lambda y: y.author, section)))


class HistoryAnalyzerTest(unittest.TestCase):

    def setUp(self) -> None:
        self.nas_model = (TEST_REPO2 / "NasModel.cs").absolute().resolve()

    def test_compute_path(self):
        hist = 'cdce762b1f46fc20c1e15c27c7874925ff830ab4'
        head = '2dee9480a4d9aff4c006467d4c4a61b7ff7b9871'

        repo = git.Repo(TURTLE_GRAPHICS_REPO)

        c_range = CommitRange(repo, head, hist)

        path = c_range.compute_path()

        self.assertIn('b26a115358829a74748b37c4f082c3ac962a3852', path)
        self.assertNotIn('dbc9cd68af1402c8803e17fb292dcaf936e6d279', path)
        self.assertIn('9518a7e739a2d7bf10708dd655a582f904a7ff7e', path)
        self.assertNotIn('eeb0d000e34557eca920fee01631bf26cfaea8f4', path)
        self.assertIn('cdce762b1f46fc20c1e15c27c7874925ff830ab4', path)

    def test_get_ownership(self):
        c_hash = '9d5b319e1302d4bfa79b44c639b1c7de82d6a9c7'
        repo = git.Repo(TEST_REPO2)
        commit_range = CommitRange(repo, c_hash, c_hash)
        ownership = get_file_changes(commit_range, c_hash, repo)

        self.assertTrue(len(ownership[self.nas_model].hunks) == 3)
        self.assertTrue(ownership[self.nas_model].hunks[0].change_start == 40)
        self.assertTrue(ownership[self.nas_model].hunks[0].length_difference == 1)
        self.assertTrue(ownership[self.nas_model].hunks[1].change_start == 51)
        self.assertTrue(ownership[self.nas_model].hunks[1].length_difference == 1)
        self.assertTrue(ownership[self.nas_model].hunks[2].change_start == 75)
        self.assertTrue(ownership[self.nas_model].hunks[2].length_difference == 1)

    def test_analyze_all_changes_by_me_first_commit(self):
        repo = git.Repo(TEST_REPO2)
        lib.try_checkout(repo, 'e4b73d4152c5e9e6c854fbf1df99011bf16e3eb9', True)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()
        self.assertTrue(result[self.nas_model].line_count == 75)

        num_changes_done_by_me = len(list(filter(lambda x: x.author == 'Michal-MK', result[self.nas_model].changes)))
        self.assertTrue(num_changes_done_by_me == result[self.nas_model].line_count)

    def test_analyze_all_changes_by_me_early_commit(self):
        repo = git.Repo(TEST_REPO2)
        lib.try_checkout(repo, '9d5b319e1302d4bfa79b44c639b1c7de82d6a9c7', True)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()
        self.assertTrue(result[self.nas_model].line_count == 78)

        num_changes_done_by_me = len(list(filter(lambda x: x.author == 'Michal-MK', result[self.nas_model].changes)))
        self.assertTrue(num_changes_done_by_me == result[self.nas_model].line_count)

    def test_analyze_all_changes_by_me(self):
        repo = git.Repo(TEST_REPO2)
        lib.try_checkout(repo, '96192b7ac9b3484a6e647519fb67f0be620f0bd5', True)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()
        self.assertTrue(result[self.nas_model].line_count == 78)

        num_changes_done_by_me = len(list(filter(lambda x: x.author == 'Michal-MK', result[self.nas_model].changes)))
        self.assertTrue(num_changes_done_by_me == result[self.nas_model].line_count)

    def test_analyze_line_distribution_between_authors(self):
        repo = git.Repo(TEST_REPO2)
        lib.try_checkout(repo, 'aa1b0d3dd95ffcbbd0827f147a912888a5ced8bd', True)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        self.assertTrue(result[self.nas_model].line_count == 85)
        self.assertTrue(by(result[self.nas_model].changes[1:75], "Michal-MK"))
        self.assertTrue(by(result[self.nas_model].changes[76:76 + 7], "Other Name"))
        self.assertTrue(by(result[self.nas_model].changes[83:85], "Michal-MK"))

    def test_analyze_percentage(self):
        repo = git.Repo(TEST_REPO2)
        lib.try_checkout(repo, 'aa1b0d3dd95ffcbbd0827f147a912888a5ced8bd', True)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        result = c_range.analyze()

        contributors = [lib.Contributor('Michal-MK', 'Michal-MK'), lib.Contributor('Other Name', 'Other Name')]

        percentage = calculate_percentage(contributors, result)

        self.assertTrue(isclose(percentage.global_contribution[contributors[0]], 77 / 84))
        self.assertTrue(isclose(percentage.global_contribution[contributors[1]], 7 / 84))

    def test_find_unmerged(self):
        repo = git.Repo(TEST_REPO_UNMERGED)
        c_range = CommitRange(repo, 'HEAD', 'ROOT')
        unmerged = c_range.find_unmerged_branches()

        self.assertTrue(len(unmerged) == 1)
        self.assertTrue(unmerged[0].name == 'second_branch')
        self.assertTrue(len(unmerged[0].path) == 3)


def test_find_unmerged_multiple(self):
    repo = git.Repo(TEST_REPO_UNMERGED_MULTIPLE)
    c_range = CommitRange(repo, 'HEAD', 'ROOT')
    unmerged = c_range.find_unmerged_branches(datetime.datetime.now().timestamp())

    unmerged.sort(key=lambda x: x.name)

    self.assertTrue(len(unmerged) == 2)
    self.assertTrue(unmerged[1].name == 'branch2')
    self.assertTrue(unmerged[0].name == 'branch1 some-tag')

    self.assertTrue(unmerged[1].head == 'a34e9dc8bc9ee55584120e40209ac97bb388fcc9')
    self.assertTrue(unmerged[0].head == '689a14b3823fafbd6bb927b5409692bdb02eb96a')

    self.assertTrue('932ccb27444ebc67fb3e83e745072902f88ec82b' in unmerged[1].path)
    self.assertTrue('676ecb3fb829d166ad8594a54b4bd8ae4b503bd5' in unmerged[0].path)

    self.assertTrue(unmerged[1].path[0] == 'b66cf3e24e6603527993578c4fea1b7f6eb322e1')
    self.assertTrue(unmerged[0].path[0] == 'b66cf3e24e6603527993578c4fea1b7f6eb322e1')

    self.assertTrue(len(unmerged[1].path) == 3)
    self.assertTrue(len(unmerged[0].path) == 3)


if __name__ == '__main__':
    unittest.main()
