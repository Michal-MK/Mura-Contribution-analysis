import copy
import re
from collections import deque
from typing import List, Dict, Tuple, Deque, Optional

from git import Repo, Commit

import lib

FileName = str
AuthorName = str
OwnershipHistory = List[Dict['FileSection', AuthorName]]

ROOT_HASH = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

HUNK_HEADER_PATTERN: re.Pattern[str] = re.compile(
    r"@@ -(\d+)(?:,(\d+))? \+(?P<change_start>\d+)(?:,(?P<change_end>\d+))? @@")


class FileSection:
    def __init__(self, prev_start: int, prev_end: int, change_start: int, change_end: int, mode: Optional[str]):
        self.prev_start = prev_start
        self.prev_end = prev_end
        self.change_start = change_start
        self.change_end = change_end
        self.mode = mode

class Change:
    def __init__(self, author: str) -> None:
        self.hunks: List[FileSection] = []
        self.author = author

    def add_hunk(self, prev_start: int, prev_end: int, change_start: int, change_end: int, mode: Optional[str] = None) -> None:
        self.hunks.append(FileSection(prev_start, prev_end, change_start, change_end, mode))


class Ownership:
    def __init__(self) -> None:
        self.history: OwnershipHistory = []
        self.changes: Dict[FileSection, AuthorName] = {}

    def add_change(self, hunk: FileSection, author: AuthorName) -> None:
        self.history.append(copy.deepcopy(self.changes))

        overlaps = [lib.overlap(hunk, existing_hunk) for existing_hunk in self.changes]

        # hunk is completely non-overlapping with existing changes
        if not any(overlaps):
            self.changes[hunk] = author
            return

        # hunk is overlapping with existing changes
        for existing in self.changes:
            if lib.overlap(hunk, existing):
                if lib.contained(hunk.change_start, existing):
                    # new hunk is starting inside existing hunk
                    if hunk.change_start == existing.change_start:
                        # new hunk starts at the same place as existing hunk
                        pass
                    elif hunk.change_start == existing.change_end:
                        # new hunk starts at the end of existing hunk
                        pass
                    else:
                        # new hunk starts inside existing hunk
                        pass
                if lib.contained(hunk.change_end, existing):
                    # new hunk is ending inside existing hunk
                    if hunk.change_end == existing.change_end:
                        # new hunk ends at the same place as existing hunk
                        pass
                    elif hunk.change_end == existing.change_start:
                        # new hunk ends at the start of existing hunk
                        pass
                    else:
                        # new hunk ends inside existing hunk
                        pass





def compute_path(current_commit_hash: str, historical_commit_hash: str, repo: Repo) -> Deque[str]:
    """
    Compute the path from <current_commit_hash> to <historical_commit_hash> in the <repo>
    :param current_commit_hash: The hash of the current commit (usually HEAD)
    :param historical_commit_hash: The hash of the historical commit (usually the first commit or the staring point)
    :param repo: The repository to analyze
    :return: A list of commit hashes sorted from <current_commit_hash> to <historical_commit_hash>
    """
    if current_commit_hash.lower() == 'head':
        current_commit_hash = repo.head.commit.hexsha
    if historical_commit_hash.lower() == 'root':
        historical_commit_hash = lib.first_commit(repo.commit(current_commit_hash))
    range = f"{current_commit_hash}...{historical_commit_hash}"
    output = repo.git.execute(["git", "rev-list", "--topo-order", "--ancestry-path", "--reverse", range])
    assert isinstance(output, str)
    ret = deque(output.splitlines())
    ret.insert(0, historical_commit_hash)
    return ret


def get_file_changes(commit_hash: str, repo: Repo) -> Dict[FileName, Change]:
    """
    Get the ownership of each file in the commit with the hash <commit_hash>
    :param commit_hash: The hash of the commit to analyze
    :param repo: The repository to analyze
    :return: A dictionary mapping each file name to the lines changed by the author of the commit
    """
    commit = repo.commit(commit_hash)
    if commit.parents:
        d = commit.parents[0].diff(commit, create_patch=True, unified=0)
    else:
        d = repo.tree(ROOT_HASH).diff(commit, create_patch=True, unified=0)

    ret = {}

    for diff in d:
        unified_diff_str = diff.diff.decode('utf-8')
        matches = HUNK_HEADER_PATTERN.findall(unified_diff_str)
        author = commit.author.name
        assert author is not None, f"Author name is None for commit {commit_hash} ({commit.message})"
        ret[diff.b_path] = Change(author)
        mode = "A" if len(matches) == 1 and diff.new_file else "M"
        for match in matches:
            prev_line_start, prev_line_end, line_start, line_end = match
            change_start = int(line_start)
            change_end = int(line_end) if line_end != '' else 0
            prev_start = int(prev_line_start)
            prev_end = int(prev_line_end) if prev_line_end != '' else 0
            ret[diff.b_path].add_hunk(prev_start, prev_end, change_start, change_end, mode)

    return ret


def analyze(current_commit_hash: str, historical_commit_hash: str, repo: Repo) -> Dict[FileName, Ownership]:
    """
    Analyze the repository <repo> from the commit with the hash <historical_commit_hash> to the commit with the hash
    <current_commit_hash>
    :param repo: The repository to analyze
    :param current_commit_hash: The hash of the current commit (usually HEAD)
    :param historical_commit_hash: The hash of the historical commit (usually the first commit or the staring point)
    :return:
    """
    path = compute_path(current_commit_hash, historical_commit_hash, repo)

    ret: Dict[FileName, Ownership] = {}

    for commit_hash in path:
        commit = repo.commit(commit_hash)
        print(f"Analyzing commit {commit_hash} ({commit.message})")
        file_ownership = get_file_changes(commit_hash, repo)
        for file_name, change in file_ownership.items():
            if file_name not in ret:
                ret[file_name] = Ownership()
            for hunk in change.hunks:
                ret[file_name].add_change(hunk, change.author)

    return ret
