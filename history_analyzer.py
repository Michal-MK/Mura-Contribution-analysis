import copy
import re
from collections import deque, defaultdict
from typing import List, Dict, Tuple, Deque, Optional, DefaultDict, Set

from git import Repo, Commit

import lib

FileName = str
AuthorName = str
AuthorPtr = int
OwnershipHistory = List[List[AuthorName]]
AnalysisResult = Dict[FileName, 'Ownership']

ROOT_HASH = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

HUNK_HEADER_PATTERN: re.Pattern[str] = re.compile(
    r"@@ -(\d+)(?:,(\d+))? \+(?P<change_start>\d+)(?:,(?P<change_end>\d+))? @@")


class CommitRange:
    def __init__(self, head: str, host: str, repo: Repo):
        self.head = head
        self.hist = host
        self.repo = repo

    def compute_path(self) -> Deque[str]:
        """
        Compute the path from <current_commit_hash> to <historical_commit_hash> in the <repo>
        :param current_commit_hash: The hash of the current commit (usually HEAD)
        :param historical_commit_hash: The hash of the historical commit (usually the first commit or the staring point)
        :param repo: The repository to analyze
        :return: A list of commit hashes sorted from <current_commit_hash> to <historical_commit_hash>
        """
        if self.head.lower() == 'head':
            self.head = self.repo.head.commit.hexsha
        if self.hist.lower() == 'root':
            self.hist = lib.first_commit(self.repo.commit(self.head)).hexsha
        range = f"{self.head}...{self.hist}"
        output = self.repo.git.execute(["git", "rev-list", "--topo-order", "--ancestry-path", "--reverse", range])
        assert isinstance(output, str)
        ret = deque(output.splitlines())
        ret.insert(0, self.hist)
        return ret

    def analyze(self) -> AnalysisResult:
        """
        Analyze the repository <repo> from the commit with the hash <historical_commit_hash> to the commit with the hash
        <current_commit_hash>
        :param repo: The repository to analyze
        :param current_commit_hash: The hash of the current commit (usually HEAD)
        :param historical_commit_hash: The hash of the historical commit (usually the first commit or the staring point)
        :return:
        """
        path = self.compute_path()

        ret: Dict[FileName, Ownership] = {}

        for commit_hash in path:
            commit = self.repo.commit(commit_hash)
            print(f"Analyzing commit {commit_hash} ({commit.message.rstrip()}) BY: {commit.author}")
            file_ownership = get_file_changes(commit_hash, self.repo)
            for file_name, change in file_ownership.items():
                if file_name not in ret:
                    assert len(change.hunks) == 1 and change.hunks[0].mode == 'A'
                    ret[file_name] = Ownership(change.hunks[0].change_end)
                for hunk in change.hunks:
                    ret[file_name].add_change(hunk, change.author)

        return ret

    def find_unmerged_branches(self):
        """
        Find all unmerged branches in the repository <repo>
        :return: A list of all unmerged branches
        """
        main_path = self.compute_path()

        head_date = self.repo.commit(self.head).committed_date
        hist_date = self.repo.commit(self.hist).committed_date

        reversed_path = list(main_path)
        reversed_path.reverse()

        all_commits = self.repo.git.execute(["git", "log", "--format=%H", "--all"]).splitlines()

        all_in_range = []
        for commit in all_commits:
            c = self.repo.commit(commit)
            if c.committed_date  <= head_date and  c.committed_date >= hist_date:
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

            print(f"Commit {parent} has contains unmerged code in at least one branch: {children}")
            path = create_path(parent, tree, self.repo, [])
            path.insert(0, parent)
            print(path)





class FileSection:
    def __init__(self, prev_start: int, prev_len: int, change_start: int, change_len: int, mode: Optional[str]):
        self.prev_start = prev_start
        self.prev_end = prev_start + prev_len
        self.prev_len = prev_len
        self.change_start = change_start
        self.change_end = change_start + change_len
        self.new_len = change_len
        self.change_len = change_len - prev_len
        self.mode = mode


class Change:
    def __init__(self, author: str) -> None:
        self.hunks: List[FileSection] = []
        self.author = author

    def add_hunk(self, prev_start: int, prev_len: int, change_start: int, change_len: int,
                 mode: Optional[str] = None) -> None:
        self.hunks.append(FileSection(prev_start, prev_len, change_start, change_len, mode))


class Ownership:
    def __init__(self, init_line_count: int) -> None:
        self.history: OwnershipHistory = []
        self.changes: List[AuthorName] = ['' for _ in range(init_line_count)]
        self._line_count = init_line_count  # Lines are indexes starting with 1
        self.line_count = init_line_count - 1

    def add_change(self, hunk: FileSection, author: AuthorName) -> None:
        self.history.append(copy.deepcopy(self.changes))

        assert hunk.change_start >= 0 and hunk.change_start <= self._line_count

        if hunk.change_len > 0 and hunk.mode != 'A':
            for i in range(hunk.change_len):
                self.changes.insert(hunk.change_start + i, '_')
            self._line_count = len(self.changes)
            self.line_count = self._line_count - 1

        for i in range(hunk.change_start, hunk.change_end):
            self.changes[i] = author


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
            prev_line_start, prev_line_len, line_start, line_len = match
            change_start = int(line_start)
            change_len = int(line_len) if line_len != '' else 1
            prev_start = int(prev_line_start)
            prev_len = int(prev_line_len) if prev_line_len != '' else 1
            ret[diff.b_path].add_hunk(prev_start, prev_len, change_start, change_len, mode)

    return ret


def calculate_percentage(result: AnalysisResult) -> Tuple[Dict[str, List[Tuple[str, float]]], Dict[str, float]]:
    ret: Dict[str, List[Tuple[str, float]]] = {}
    author_total: DefaultDict[str, int] = defaultdict(lambda: 0)
    lines_total = 0

    for key, val in result.items():
        ret[key] = []
        intermediate: DefaultDict[str, int] = defaultdict(lambda: 0)
        for author in val.changes[1:]:
            intermediate[author] = intermediate[author] + 1
            author_total[author] = author_total[author] + 1
            lines_total += 1
        file_lines = len(val.changes[1:])
        for author, lines in intermediate.items():
            ret[key].append((author, lines / file_lines))

    totals = {}

    for author, authors_total_lines in author_total.items():
        totals[author] = authors_total_lines / lines_total

    return ret, totals

def construct_unmerged_tree(unmerged_commits: Set[str], all_commits: Set[str], repo: Repo) -> Dict[str, List[str]]:
    """
    Construct a tree of all unmerged commits
    :param unmerged_commits: A set of all unmerged commits
    :param all_commits: A list of all commits in the repository
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
