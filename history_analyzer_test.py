import unittest
from math import isclose
from typing import List

import git

import lib
from history_analyzer import get_file_changes, AuthorName, CommitRange, calculate_percentage

TEST_REPO = "C:\\Repositories\\TurtleGraphics"
TEST_REPO2 = ".\\repositories\\single_file"
TEST_REPO_UNMERGED = ".\\repositories\\unmerged"

def by(section: List[AuthorName], author: AuthorName):
    return all(filter(lambda x: x == author, section))

def compute_path_t():
    hist = 'cdce762b1f46fc20c1e15c27c7874925ff830ab4'
    head = '2dee9480a4d9aff4c006467d4c4a61b7ff7b9871'
    repo = git.Repo(TEST_REPO)

    c_range = CommitRange(head, hist, repo)

    path = c_range.compute_path()

    assert 'b26a115358829a74748b37c4f082c3ac962a3852' in path
    assert 'dbc9cd68af1402c8803e17fb292dcaf936e6d279' not in path
    assert '9518a7e739a2d7bf10708dd655a582f904a7ff7e' in path
    assert 'eeb0d000e34557eca920fee01631bf26cfaea8f4' not in path
    assert 'cdce762b1f46fc20c1e15c27c7874925ff830ab4' in path


def get_ownership_t():
    c_hash = '9d5b319e1302d4bfa79b44c639b1c7de82d6a9c7'
    repo = git.Repo(TEST_REPO2)
    ownership = get_file_changes(c_hash, repo)

    assert len(ownership['NasModel.cs'].hunks) == 3
    assert ownership['NasModel.cs'].hunks[0].change_start == 40
    assert ownership['NasModel.cs'].hunks[0].change_len == 1
    assert ownership['NasModel.cs'].hunks[1].change_start == 51
    assert ownership['NasModel.cs'].hunks[1].change_len == 1
    assert ownership['NasModel.cs'].hunks[2].change_start == 75
    assert ownership['NasModel.cs'].hunks[2].change_len == 1


def analyze_t1():
    repo = git.Repo(TEST_REPO2)
    lib.set_repo(repo)
    lib.try_checkout('e4b73d4152c5e9e6c854fbf1df99011bf16e3eb9', True)
    c_range = CommitRange('HEAD', 'ROOT', repo)
    result = c_range.analyze()
    assert result['NasModel.cs'].line_count == 75
    assert result['NasModel.cs'].changes[0] == ''
    assert len(list(filter(lambda x: x == 'Michal-MK', result['NasModel.cs'].changes))) == result[
        'NasModel.cs'].line_count


def analyze_t2():
    repo = git.Repo(TEST_REPO2)
    lib.set_repo(repo)
    lib.try_checkout('9d5b319e1302d4bfa79b44c639b1c7de82d6a9c7', True)
    c_range = CommitRange('HEAD', 'ROOT', repo)
    result = c_range.analyze()
    assert result['NasModel.cs'].line_count == 78
    assert result['NasModel.cs'].changes[0] == ''
    assert len(list(filter(lambda x: x == 'Michal-MK', result['NasModel.cs'].changes))) == result[
        'NasModel.cs'].line_count


def analyze_t3():
    repo = git.Repo(TEST_REPO2)
    lib.set_repo(repo)
    lib.try_checkout('96192b7ac9b3484a6e647519fb67f0be620f0bd5', True)
    c_range = CommitRange('HEAD', 'ROOT', repo)
    result = c_range.analyze()
    assert result['NasModel.cs'].line_count == 78
    assert result['NasModel.cs'].changes[0] == ''
    assert len(list(filter(lambda x: x == 'Michal-MK', result['NasModel.cs'].changes))) == result[
        'NasModel.cs'].line_count


def analyze_t4():
    repo = git.Repo(TEST_REPO2)
    lib.set_repo(repo)
    lib.try_checkout('aa1b0d3dd95ffcbbd0827f147a912888a5ced8bd', True)
    c_range = CommitRange('HEAD', 'ROOT', repo)
    result = c_range.analyze()
    assert result['NasModel.cs'].line_count == 85
    assert result['NasModel.cs'].changes[0] == ''
    assert by(result['NasModel.cs'].changes[1:75], "Michal-MK")
    assert by(result['NasModel.cs'].changes[76:76 + 7], "Other Name")
    assert by(result['NasModel.cs'].changes[83:85], "Michal-MK")

def percentage_t():
    repo = git.Repo(TEST_REPO2)
    lib.set_repo(repo)
    lib.try_checkout('aa1b0d3dd95ffcbbd0827f147a912888a5ced8bd', True)
    c_range = CommitRange('HEAD', 'ROOT', repo)
    result = c_range.analyze()

    res = calculate_percentage(result)

    assert isclose(res[1]['Michal-MK'], 78 / 85)
    assert isclose(res[1]['Other Name'], 7 / 85)

def find_unmerged_t():
    repo = git.Repo(TEST_REPO_UNMERGED)
    lib.set_repo(repo)
    c_range = CommitRange('HEAD', 'ROOT', repo)
    unmerged = c_range.find_unmerged_branches()


if __name__ == '__main__':
    compute_path_t()
    get_ownership_t()
    analyze_t1()
    analyze_t2()
    analyze_t3()
    analyze_t4()
    percentage_t()
    find_unmerged_t()
