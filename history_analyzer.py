import copy
import re
from collections import deque, defaultdict
from pathlib import Path
from typing import List, Dict, Tuple, Deque, Optional, DefaultDict, Set

import git
import lib

from lib import Percentage, first_commit, repo_p, Contributor, find_contributor

from git import Repo

from uni_chars import *

AuthorName = str
AuthorPtr = int
OwnershipHistory = List[List[AuthorName]]
AnalysisResult = Dict[Path, 'Ownership']

ROOT_HASH = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

HUNK_HEADER_PATTERN: re.Pattern[str] = re.compile(
    r"@@ -(\d+)(?:,(\d+))? \+(?P<change_start>\d+)(?:,(?P<change_end>\d+))? @@")


class CommitHistory:
    def __init__(self, name: str, path: List[str]):
        self.name = name
        self.path = path

    @property
    def head(self) -> str:
        return self.path[-1] if len(self.path) > 0 else ''


class CommitRange:
    def __init__(self, head: str, hist: str, repo: Optional[Repo] = None, verbose=False):
        self.head = head
        self.hist = hist
        if repo is None:
            if lib.REPO is None:
                raise ValueError(f"{ERROR} No repository set! Did you evaluate all code blocks above?")
            self.repo = lib.REPO
        else:
            self.repo = repo

        if self.head.lower() == 'head':
            self.head = self.repo.head.commit.hexsha
        if self.hist.lower() == 'root':
            self.hist = first_commit(self.repo.commit(self.head)).hexsha
        marks = self.repo.git.execute(["git", "show-ref", "--heads", "--tags"])
        assert isinstance(marks, str)

        merged_marked_commits = [y.split() for y in marks.splitlines()]
        marked_commits = [(str(x[0]), str(x[1]).replace('refs/heads/', '').replace('refs/tags/', ''))
                          for x in merged_marked_commits]

        for mk in marked_commits:
            if mk[1] == self.head:
                self.head = mk[0]
            if mk[1] == self.hist:
                self.hist = mk[0]

        self.head_commit: git.Commit = self.repo.commit(self.head)
        self.hist_commit: git.Commit = self.repo.commit(self.hist)

        if verbose:
            print(f"{SUCCESS} Commit range: {self.head}...{self.hist}")
            print(f" - Final commit on: {self.head_commit.committed_datetime}")
            print(f" - Initial commit on: {self.hist_commit.committed_datetime}")

    def __iter__(self):
        for commit in self.compute_path():
            yield commit

    def compute_path(self) -> Deque[str]:
        """
        Compute the path from <current_commit_hash> to <historical_commit_hash> in the <repo>
        :return: A list of commit hashes sorted from <current_commit_hash> to <historical_commit_hash>
        """
        c_range = f"{self.head}...{self.hist}"
        output = self.repo.git.execute(["git", "rev-list", "--topo-order", "--ancestry-path", "--reverse", c_range])
        assert isinstance(output, str)
        ret = deque(output.splitlines())
        ret.insert(0, self.hist)
        return ret

    def checkout_file_from(self, commit_hash: str, file_name: str) -> None:
        """
        Checkout the file <file_name> from the parent of the commit with the hash <commit_hash>
        :param commit_hash:
        :param file_name:
        :return:
        """
        commit = self.repo.commit(commit_hash)
        self.repo.git.checkout(commit.hexsha, '--', file_name)

    def populate_previously_unseen_file(self, change: 'Change', commit_hash: str, file_name: str,
                                        ret: Dict[Path, 'Ownership']) -> None:
        cmd = ['git', 'cat-file', '-e', change.hunks[0].prev_file_hexsha]
        status, sout, serr = self.repo.git.execute(cmd, with_extended_output=True)
        if status == 0:
            # Obtain the previous version of the file as a base
            file_path = repo_p(file_name)
            self.checkout_file_from(commit_hash, file_path)
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            ret[file_path] = Ownership(len(content.splitlines()))
            for hunk in change.hunks:
                ret[file_path].add_change(hunk, change.author)

    def analyze(self) -> AnalysisResult:
        """
        Analyze the repository <repo> from the commit with the hash <historical_commit_hash> to the commit with the hash
        <current_commit_hash>
        :return:
        """
        path = self.compute_path()

        ret: Dict[Path, Ownership] = {}

        for commit_hash in path:
            # print(f"Analyzing commit {commit_hash} ({commit.message.rstrip()}) BY: {commit.author}")
            file_ownership = get_file_changes(commit_hash, self.repo)
            for file_name, change in file_ownership.items():
                if file_name not in ret:
                    if change.hunks and change.hunks[0].mode == 'R':
                        assert change.previous_name is not None
                        if change.previous_name in ret:
                            ret[file_name] = ret[change.previous_name]
                            del ret[change.previous_name]
                        else:
                            self.populate_previously_unseen_file(change, commit_hash, str(file_name), ret)
                        for hunk in change.hunks:
                            ret[file_name].add_change(hunk, change.author)
                    elif change.hunks and change.hunks[0].mode == 'A':
                        ret[file_name] = Ownership(change.hunks[0].change_end, change.author)
                    elif not change.hunks:
                        # This is a binary file
                        ret[file_name] = Ownership(-1, change.author)
                    elif change.hunks[0].mode == 'M':
                        # This file already existed in the repo, this can occur if the analysis does not
                        # start from the first commit
                        self.populate_previously_unseen_file(change, commit_hash, str(file_name), ret)
                    continue

                elif file_name in ret and change.hunks and change.hunks[0].mode == 'A' and not ret[file_name].exists:
                    # This file was deleted in a previous commit and re-added in this commit
                    ret[file_name].exists = True
                    ret[file_name].history.append(ret[file_name].changes)
                    ret[file_name].changes = [change.author for _ in range(change.hunks[0].change_end)]
                    ret[file_name]._line_count = change.hunks[0].change_end  # Lines are indexes starting with 1
                    ret[file_name].line_count = change.hunks[0].change_end - 1
                    continue

                elif file_name in ret and change.hunks and change.hunks[0].mode == 'D':
                    ret[file_name].delete()
                    continue

                for hunk in change.hunks:
                    if file_name not in ret and hunk.mode == 'D':
                        continue
                    if file_name in ret and hunk.mode == 'A':
                        # This file was added in a previous commit as well as in this commit
                        # Likely a conflict down the line
                        continue
                    ret[file_name].add_change(hunk, change.author)

        return ret

    def find_unmerged_branches(self, end_date: Optional[float] = None) -> List[CommitHistory]:
        """
        Find all unmerged branches in the repository <repo>
        :return: A list of all unmerged branches
        """
        main_path = self.compute_path()

        head_date = end_date if end_date is not None else self.repo.commit(self.head).committed_date
        hist_date = self.repo.commit(self.hist).committed_date

        reversed_path = list(main_path)
        reversed_path.reverse()

        result = self.repo.git.execute(["git", "log", "--format=%H", "--all"])
        assert isinstance(result, str)
        all_commits = result.splitlines()

        all_in_range = []
        for commit in all_commits:
            c = self.repo.commit(commit)
            if c.committed_date <= head_date and c.committed_date >= hist_date:
                all_in_range.append(commit)

        all_set = set(all_in_range)
        unmerged_commits = all_set.difference(main_path)

        tree = construct_unmerged_tree(unmerged_commits, all_set, self.repo)

        visited = set()
        for parent, children in filter(lambda x: x[1], tree.items()):
            if parent in unmerged_commits:
                continue
            if parent in visited:
                continue
            assert parent in main_path, f"Parent commit: {parent} not on the main path!"

            visited.add(parent)

            ret: List[CommitHistory] = []

            for child in children:
                path = []
                identifier: str = ""
                visited.add(child)
                while child in tree:
                    path.append(child)
                    _parent = child
                    child = tree[child]
                    if isinstance(child, list):
                        if len(child) > 1:
                            print(f"The unmerged branch branches again.")
                            break
                        if len(child) == 0:
                            identifier = (self.repo.git.execute(f'git branch --contains {_parent}').strip() + " " +
                                          self.repo.git.execute(f'git tag --contains {_parent}').strip()).strip()
                            break
                        child = child[0]
                path.insert(0, parent)
                ret.append(CommitHistory(identifier, path))
            return ret


class FileSection:
    def __init__(self, prev_start: int, prev_len: int, change_start: int, change_len: int, prev_file_hexsha,
                 mode: Optional[str]):
        self.prev_start = prev_start
        self.prev_end = prev_start + prev_len
        self.prev_len = prev_len
        self.change_start = change_start
        self.change_end = change_start + change_len
        self.new_len = change_len
        self.change_len = change_len - prev_len
        self.prev_file_hexsha = prev_file_hexsha
        self.mode = mode

    def __repr__(self):
        return f"FileSection(prev={self.prev_start}-{self.prev_end} ({self.prev_len}), " \
               f"change={self.change_start}-{self.change_end} ({self.new_len}/{self.change_len}), " \
               f"prev_file_hexsha={self.prev_file_hexsha}, mode={self.mode})"


class Change:
    def __init__(self, author: str) -> None:
        self.hunks: List[FileSection] = []
        self.author = author
        self.previous_name: Optional[Path] = None
        self.is_binary = False

    def add_hunk(self, prev_start: int, prev_len: int, change_start: int, change_len: int,
                 previous_file_hexsha: bytes, mode: Optional[str] = None) -> None:
        self.hunks.append(FileSection(prev_start, prev_len, change_start, change_len, previous_file_hexsha, mode))


class Ownership:
    def __init__(self, init_line_count: int, author: str = '') -> None:
        self.history: OwnershipHistory = []
        self.changes: List[AuthorName] = [author for _ in range(init_line_count)]
        if not self.changes or init_line_count == -1:
            # Empty file or binary file
            self.changes = [author]
        self.changes[0] = ''
        self._line_count = init_line_count  # Lines are indexes starting with 1
        self.line_count = init_line_count - 1
        self.exists = True

    def delete(self):
        self.history.append(copy.deepcopy(self.changes))
        self.changes = []
        self._line_count = 0
        self.line_count = 0
        self.exists = False

    def add_change(self, hunk: FileSection, author: AuthorName) -> None:
        self.history.append(copy.deepcopy(self.changes))

        assert hunk.mode != 'A', "This function can only be used to add changes to existing files."

        if self._line_count == -1:
            # This is a binary file
            self.changes[0] = author
            return

        try:
            assert hunk.change_start >= 0 and hunk.change_start <= self._line_count, \
                f"Change start {hunk.change_start} is out of bounds for file with {self._line_count} lines."
        except AssertionError as e:
            pass
        if hunk.change_len > 0:
            for i in range(hunk.change_len):
                self.changes.insert(hunk.change_start + i, '_')
            self._line_count = len(self.changes)
            self.line_count = self._line_count - 1

        for i in range(hunk.change_start, hunk.change_end):
            self.changes[i] = author

    def __str__(self):
        return f"Ownership(lines={self.line_count}, changes={self.changes})"


def get_file_changes(commit_hash: str, repo: Repo) -> Dict[Path, Change]:
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
        try:
            unified_diff_str = diff.diff.decode('utf-8')
        except UnicodeDecodeError:
            unified_diff_str = diff.diff.decode('latin-1')
            # Fallback decode to latin-1
        matches = HUNK_HEADER_PATTERN.findall(unified_diff_str)
        author = commit.author.name
        assert author is not None, f"Author name is None for commit {commit_hash} ({commit.message})"
        actual_path = repo_p(diff.b_path) if diff.b_path is not None else repo_p(diff.a_path)
        if diff.b_path is None:
            ret[actual_path] = Change(author)
            mode = "D"
        else:
            ret[actual_path] = Change(author)
            mode = "A" if diff.new_file else "M"
        if diff.renamed:
            mode = "R"
            ret[actual_path].previous_name = repo_p(diff.a_path)
        for match in matches:
            prev_line_start, prev_line_len, line_start, line_len = match
            change_start = int(line_start)
            change_len = int(line_len) if line_len != '' else 1
            prev_start = int(prev_line_start)
            prev_len = int(prev_line_len) if prev_line_len != '' else 1
            ret[actual_path].add_hunk(prev_start, prev_len, change_start, change_len,
                                      diff.a_blob.hexsha if diff.a_blob is not None else diff.b_blob.hexsha, mode)
        if not matches:
            # no matches
            ret[actual_path].is_binary = True

    return ret


def calculate_percentage(contributors: List[Contributor], result: AnalysisResult) -> Percentage:
    ret: Dict[Path, List[Tuple[Contributor, float]]] = {}
    author_total: DefaultDict[Contributor, int] = defaultdict(lambda: 0)
    lines_total = 0

    for path, val in result.items():
        ret[path] = []
        intermediate: DefaultDict[Contributor, int] = defaultdict(lambda: 0)
        for author in val.changes[1:]:
            contributor = find_contributor(contributors, author)
            assert contributor is not None, f"Could not find contributor for author {author}"
            intermediate[contributor] = intermediate[contributor] + 1
            author_total[contributor] = author_total[contributor] + 1
            lines_total += 1
        file_lines = len(val.changes[1:])
        for contributor, lines in intermediate.items():
            ret[path].append((contributor, lines / file_lines))

    totals: DefaultDict = defaultdict(lambda: 0)

    for contributor, authors_total_lines in author_total.items():
        totals[contributor] = authors_total_lines / lines_total

    return Percentage(ret, totals)


def construct_unmerged_tree(unmerged_commits: Set[str], all_commits: Set[str], repo: Repo) -> Dict[str, List[str]]:
    """
    Construct a tree of all unmerged commits
    :param unmerged_commits: A set of all unmerged commits
    :param all_commits: A list of all commits in the repository
    :param repo: The repository to analyze
    :return: A dictionary mapping each commit to a list of its children
    """
    ret: Dict[str, List[str]] = {}
    for commit in all_commits:
        ret[commit] = []

    visited: Set[str] = set()
    q: Deque[str] = deque()

    for commit in unmerged_commits:
        q.append(commit)
        while q:
            curr = q.popleft()
            if curr in visited:
                continue
            visited.add(curr)
            for parent in repo.commit(curr).parents:
                if parent.hexsha in all_commits:
                    ret[parent.hexsha].append(curr)
                    if parent.hexsha in unmerged_commits:
                        q.append(parent.hexsha)
    return ret


def create_path(parent: str, tree: Dict[str, List[str]], repo: Repo, paths: List[str]) -> List[str]:
    ret: List[str] = []
    children = tree[parent]
    for child in children:
        ret.append(child)
        ret.extend(create_path(child, tree, repo, paths))
    return ret
