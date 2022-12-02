import unittest

import git

from history_analyzer import compute_path, get_file_changes, analyze

TEST_REPO = "C:\\Repositories\\TurtleGraphics"
TEST_REPO2 = ".\\repositories\\single_file"


def compute_path_t():
    start_hash = 'cdce762b1f46fc20c1e15c27c7874925ff830ab4'
    end_hash = '2dee9480a4d9aff4c006467d4c4a61b7ff7b9871'
    repo = git.Repo(TEST_REPO)

    path = compute_path(end_hash, start_hash, repo)

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
    assert ownership['NasModel.cs'].hunks[0][2] == 40
    assert ownership['NasModel.cs'].hunks[0][3] == 0
    assert ownership['NasModel.cs'].hunks[1][2] == 51
    assert ownership['NasModel.cs'].hunks[1][3] == 0
    assert ownership['NasModel.cs'].hunks[2][2] == 75
    assert ownership['NasModel.cs'].hunks[2][3] == 0


def analyze_t():
    repo = git.Repo(TEST_REPO2)
    result = analyze('HEAD', 'ROOT', repo)
    print(result)


if __name__ == '__main__':
    compute_path_t()
    get_ownership_t()
    analyze_t()
