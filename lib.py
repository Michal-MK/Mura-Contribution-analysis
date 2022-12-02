from typing import Union, List, Optional, Literal

from git import Repo, Commit

from history_analyzer import FileSection

REPO: Repo

def set_repo(repo: Union[str, Repo]) -> None:
    global REPO
    if isinstance(repo, str):
        REPO = Repo(repo)
    else:
        REPO = repo

def first_commit(commit: Commit) -> Commit:
    while commit.parents:
        commit = commit.parents[0]
    return commit


def file_contents(commit: Commit, file: str) -> str:
    return REPO.git.show(f'{commit.hexsha}:{file}')

def commit_summary(commit : Commit) -> None:
    print(f"There are total of {commit.stats.total['files']} changed files")
    print(f"Author: {commit.author}")
    print(f"Message: {commit.message}")

def stats_for_contributor(contributor: str) -> None:
    insertions = 0
    deletions = 0
    print(f"Stats for {contributor}:")
    for commit in REPO.iter_commits():
        if commit.author.name == contributor:
            # thanks_python_for_not_letting_me_inline_this_variable = commit.message.split('\n')[0]
            # print(f"Commit: {thanks_python_for_not_letting_me_inline_this_variable}")
            # print(commit.stats.total)
            insertions += commit.stats.total['insertions']
            deletions += commit.stats.total['deletions']
    print(f"Total insertions: {insertions}")
    print(f"Total deletions: {deletions}")

def get_files_with_flag(commit: Commit, flag: Literal["A", "R", "D", "M"]) -> List[str]:
    print(f"Files with flag {flag}:")
    parent: Optional[Commit] = None
    if commit.parents:
        parent = commit.parents[0]

    if parent is None and flag != "A":
        return []
    if parent is None and flag == "A":
        return [file.name for file in commit.tree.blobs]

    files = []
    for diff in commit.diff(parent):
        if diff.change_type == flag:
            files.append(diff.b_path)
    return files

def try_checkout(commit_hash: str) -> None:
    try:
        REPO.git.checkout(commit_hash)
    except:
        print(f"Failed to checkout {commit_hash} - Are there any uncommitted changes?")


def overlap(hunk: FileSection, existing_hunk: FileSection):
    if hunk.mode == "A":
        return False

    if hunk.change_start <= existing_hunk.change_start <= hunk.change_end:
        return True
    if hunk.change_start <= existing_hunk.change_end <= hunk.change_end:
        return True
    if existing_hunk.change_start <= hunk.change_start <= existing_hunk.change_end:
        return True
    if existing_hunk.change_start <= hunk.change_end <= existing_hunk.change_end:
        return True
    return False


def contained(point: int, existing: FileSection):
    return point >= existing.change_start and point <= existing.change_end