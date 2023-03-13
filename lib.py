import os
from pathlib import Path
from typing import Union, List, Optional, Literal

import git
from git import Repo, Commit

REPO: Repo
ignore_list = os.path.join(Path(__file__).parent, "data", "ignore-list.txt")


class FileGroup:
    def __init__(self, name: str, files: List[Path]):
        self.name = name
        self.files = files

    def get_common_extension(self):
        extensions = []
        for file in self.files:
            extensions.append(file.suffix)
        return max(set(extensions), key=extensions.count)

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

def try_checkout(commit_hash: str, force: bool = False) -> None:
    try:
        REPO.git.checkout(commit_hash, force=force)
    except Exception as e:
        print(f"Failed to checkout {commit_hash} {e} - Are there any uncommitted changes?")


def _ignored_files() -> List[str]:
    """
    Get a list of all ignored files
    :return: A list of all ignored files
    """
    ret: List[str] = []
    with open(ignore_list, 'r') as f:
        for line in f:
            if line.isspace() or line.startswith('#') \
                    or line.startswith('/'):  # This is not supported by `pathlib.Path.rglob`
                continue
            ret.append(line.strip())
    return ret


def get_tracked_files(project_root: Union[Path, git.Repo]) -> List[FileGroup]:
    """
    Find all files that are related, relative to the project root
    :
    :param project_root: The root directory of the project
    :return: A dictionary of all directories and their files which are related to each other
    """
    ret: List[FileGroup] = []

    if isinstance(project_root, git.Repo):
        project_root = Path(project_root.working_dir)

    for root, dirs, files in os.walk(project_root):
        to_remove = []
        for directory in dirs:
            if is_ignored(Path(root).joinpath(directory)) or directory == '.git':
                to_remove.append(directory)
        for directory in to_remove:
            dirs.remove(directory)
        file_group = FileGroup(root, [])
        for file in files:
            if is_ignored(Path(root).joinpath(file)):
                continue
            file_group.files.append(Path(root).joinpath(file))
        if file_group.files:
            ret.append(file_group)

    return ret


def is_ignored(file: Path) -> bool:
    """
    Check if a file is ignored
    :param file: The file to check
    :return: True if the file is ignored, False otherwise
    """
    ignored = _ignored_files()
    for ignore in ignored:
        if file.match(ignore):
            return True
    return False


def filter_related_groups(groups: List[FileGroup]) -> List[FileGroup]:
    """
    Filter groups such that only groups with a high file similarity are returned
    :param groups: A list of all folders containing possibly related files
    """
    ret: List[FileGroup] = []
    for group in groups:
        # folders containing only one or two files are not interesting
        if len(group.files) <= 2:
            continue
        ext = group.get_common_extension()
        common_files = [f for f in group.files if Path(f).suffix == ext]
        # folders containing only one or two files of the same type are not interesting
        if len(common_files) <= 2:
            continue

        ret.append(group)

    return ret


def repo_p(file_name: str, repo: Repo):
    return os.path.join(repo.common_dir, '..', file_name)