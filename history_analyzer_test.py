import unittest
from math import isclose
from typing import List

import git

import lib
from environment import TURTLE_GRAPHICS_REPO
from history_analyzer import get_file_changes, AuthorName, CommitRange, calculate_percentage

TEST_REPO2 = ".\\repositories\\single_file"
TEST_REPO_UNMERGED = ".\\repositories\\unmerged"


def by(section: List[AuthorName], author: AuthorName):
    return all(filter(lambda x: x == author, section))


class HistoryAnalyzerTest(unittest.TestCase):
    def test_compute_path(self):
        hist = 'cdce762b1f46fc20c1e15c27c7874925ff830ab4'
        head = '2dee9480a4d9aff4c006467d4c4a61b7ff7b9871'
        repo = git.Repo(TURTLE_GRAPHICS_REPO)

        c_range = CommitRange(head, hist, repo)

        path = c_range.compute_path()

        self.assertIn('b26a115358829a74748b37c4f082c3ac962a3852', path)
        self.assertNotIn('dbc9cd68af1402c8803e17fb292dcaf936e6d279', path)
        self.assertIn('9518a7e739a2d7bf10708dd655a582f904a7ff7e', path)
        self.assertNotIn('eeb0d000e34557eca920fee01631bf26cfaea8f4', path)
        self.assertIn('cdce762b1f46fc20c1e15c27c7874925ff830ab4', path)

    def test_get_ownership(self):
        c_hash = '9d5b319e1302d4bfa79b44c639b1c7de82d6a9c7'
        repo = git.Repo(TEST_REPO2)
        ownership = get_file_changes(c_hash, repo)

        self.assertTrue(len(ownership['NasModel.cs'].hunks) == 3)
        self.assertTrue(ownership['NasModel.cs'].hunks[0].change_start == 40)
        self.assertTrue(ownership['NasModel.cs'].hunks[0].change_len == 1)
        self.assertTrue(ownership['NasModel.cs'].hunks[1].change_start == 51)
        self.assertTrue(ownership['NasModel.cs'].hunks[1].change_len == 1)
        self.assertTrue(ownership['NasModel.cs'].hunks[2].change_start == 75)
        self.assertTrue(ownership['NasModel.cs'].hunks[2].change_len == 1)

    def test_analyze_1(self):
        repo = git.Repo(TEST_REPO2)
        lib.set_repo(repo)
        lib.try_checkout('e4b73d4152c5e9e6c854fbf1df99011bf16e3eb9', True)
        c_range = CommitRange('HEAD', 'ROOT', repo)
        result = c_range.analyze()
        self.assertTrue(result['NasModel.cs'].line_count == 75)
        self.assertTrue(result['NasModel.cs'].changes[0] == '')

        num_changes_done_by_me = len(list(filter(lambda x: x == 'Michal-MK', result['NasModel.cs'].changes)))
        self.assertTrue(num_changes_done_by_me == result['NasModel.cs'].line_count)

    def test_analyze_2(self):
        repo = git.Repo(TEST_REPO2)
        lib.set_repo(repo)
        lib.try_checkout('9d5b319e1302d4bfa79b44c639b1c7de82d6a9c7', True)
        c_range = CommitRange('HEAD', 'ROOT', repo)
        result = c_range.analyze()
        self.assertTrue(result['NasModel.cs'].line_count == 78)
        self.assertTrue(result['NasModel.cs'].changes[0] == '')

        num_changes_done_by_me = len(list(filter(lambda x: x == 'Michal-MK', result['NasModel.cs'].changes)))
        self.assertTrue(num_changes_done_by_me == result['NasModel.cs'].line_count)

    def test_analyze_3(self):
        repo = git.Repo(TEST_REPO2)
        lib.set_repo(repo)
        lib.try_checkout('96192b7ac9b3484a6e647519fb67f0be620f0bd5', True)
        c_range = CommitRange('HEAD', 'ROOT', repo)
        result = c_range.analyze()
        self.assertTrue(result['NasModel.cs'].line_count == 78)
        self.assertTrue(result['NasModel.cs'].changes[0] == '')

        num_changes_done_by_me = len(list(filter(lambda x: x == 'Michal-MK', result['NasModel.cs'].changes)))
        self.assertTrue(num_changes_done_by_me == result['NasModel.cs'].line_count)

    def test_analyze_4(self):
        repo = git.Repo(TEST_REPO2)
        lib.set_repo(repo)
        lib.try_checkout('aa1b0d3dd95ffcbbd0827f147a912888a5ced8bd', True)
        c_range = CommitRange('HEAD', 'ROOT', repo)
        result = c_range.analyze()

        self.assertTrue(result['NasModel.cs'].line_count == 85)
        self.assertTrue(result['NasModel.cs'].changes[0] == '')
        self.assertTrue(by(result['NasModel.cs'].changes[1:75], "Michal-MK"))
        self.assertTrue(by(result['NasModel.cs'].changes[76:76 + 7], "Other Name"))
        self.assertTrue(by(result['NasModel.cs'].changes[83:85], "Michal-MK"))

    def test_percentage(self):
        repo = git.Repo(TEST_REPO2)
        lib.set_repo(repo)
        lib.try_checkout('aa1b0d3dd95ffcbbd0827f147a912888a5ced8bd', True)
        c_range = CommitRange('HEAD', 'ROOT', repo)
        result = c_range.analyze()

        res = calculate_percentage(result)

        self.assertTrue(isclose(res[1]['Michal-MK'], 78 / 85))
        self.assertTrue(isclose(res[1]['Other Name'], 7 / 85))

    def test_find_unmerged(self):
        repo = git.Repo(TEST_REPO_UNMERGED)
        lib.set_repo(repo)
        c_range = CommitRange('HEAD', 'ROOT', repo)
        unmerged = c_range.find_unmerged_branches()


if __name__ == '__main__':
    unittest.main()
