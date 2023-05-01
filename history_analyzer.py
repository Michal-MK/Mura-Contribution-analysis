import copy
import datetime
import re
from collections import deque, defaultdict
from datetime import timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Deque, Optional, DefaultDict, Set, Union

from configuration import Configuration
from lib import Percentage, first_commit, repo_p, Contributor, find_contributor, posix_repo_p

from git import Repo, Commit, DiffIndex

from uni_chars import *

AuthorName = str

AnalysisResult = Dict[Path, 'Ownership']

ROOT_HASH = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'

HUNK_HEADER_PATTERN: re.Pattern[str] = re.compile(
    r"@@ -(\d+)(?:,(\d+))? \+(?P<change_start>\d+)(?:,(?P<change_end>\d+))? @@")

HUNK_CONFLICT_PATTERN: re.Pattern[str] = re.compile(
    r"@@@ -(\d+)(?:,(\d+))? -(\d+)(?:,(\d+))? \+(?P<change_start>\d+)(?:,(?P<change_end>\d+))? @@@")

CONFLICT_A_NAME: re.Pattern = re.compile(r"--- a/(.*)\s")
CONFLICT_B_NAME: re.Pattern = re.compile(r"\+\+\+ b/(.*)\s")


class OwnershipHistory:
    def __init__(self, commit: str, content: List['LineMetadata'], lines_changed: int):
        self.commit = commit
        self.content = content
        self.lines_changed = lines_changed

    def __str__(self):
        return f"{self.commit} - Lines: {len(self.content)}"

    def __repr__(self):
        return self.__str__()


class LineMetadata:
    def __init__(self, author: str, content: str, change_date: datetime.datetime):
        self.author = author
        self.content = content
        self.change_date = change_date

    @property
    def is_blank(self):
        return self.content == '' or self.content.strip() == ''

    def __str__(self):
        return f"{self.author}: {self.content}"

    def __repr__(self):
        return self.__str__()


class CommitHistory:
    def __init__(self, name: str, path: List[str]):
        self.name = name
        self.path = path

    @property
    def head(self) -> str:
        return self.path[-1] if len(self.path) > 0 else ''


class CommitRange:
    def __init__(self, repo: Repo, head: str, hist: str, verbose=False):
        self.head = head
        self.hist = hist
        self.ownership_overrides: Dict[str, str] = {}
        if repo is None:
            raise ValueError(f"{ERROR} No repository set! Did you evaluate all code blocks above?")
        else:
            self.repo = repo

        if self.head.lower() == 'head':
            self.head = self.repo.head.commit.hexsha
        if self.hist.lower() == 'root':
            self.hist = first_commit(self.repo.commit(self.head)).hexsha
        marks = self.repo.git.execute(["git", "show-ref", "--heads", "--tags"])
        remote_marks = self.repo.git.execute(['git', 'branch', '-r'])
        assert isinstance(marks, str) and isinstance(remote_marks, str)

        remote_marked_commits = [y.split() for y in remote_marks.splitlines() if len(y.split()) == 1]

        merged_marked_commits = [y.split() for y in marks.splitlines()]

        to_remove = []

        for x in merged_marked_commits:
            if x[1].startswith('refs/tags'):
                resolved = self.repo.git.execute(['git', 'rev-list', '-n', '1', x[1]])
                assert isinstance(resolved, str)
                idx = list(map(lambda x: x[0], merged_marked_commits)).index(resolved)
                merged_marked_commits[idx][1] = merged_marked_commits[idx][1] + ' ' + x[1]
                to_remove.append(x)

        for x in to_remove:
            merged_marked_commits.remove(x)

        marker_list = [(str(x[0]), str(x[1]).replace('refs/heads/', '').replace('refs/tags/', ''))
                       for x in merged_marked_commits]

        for name in remote_marked_commits:
            marker_list.append((self.repo.git.execute(['git', 'rev-parse', name[0]]), name[0]))

        self.marked_commits = dict()
        for sha, name in marker_list:
            self.marked_commits[sha] = name

        for mk in self.marked_commits.items():
            if mk[1] == self.head:
                self.head = mk[0]
            if mk[1] == self.hist:
                self.hist = mk[0]

        self.head_commit: Commit = self.commit(self.head)
        self.hist_commit: Commit = self.commit(self.hist)

        if verbose:
            print(f"{SUCCESS} Commit range: {self.head}...{self.hist}")
            print(f" - Final commit on: {self.head_commit.committed_datetime}")
            print(f" - Initial commit on: {self.hist_commit.committed_datetime}")

    def commit(self, commit_hash: str) -> Commit:
        orig_commit = self.repo.commit(commit_hash)
        if commit_hash in self.ownership_overrides:
            orig_commit.author.name = self.ownership_overrides[commit_hash]
            orig_commit.author.email = f'<OVERRIDEN>{orig_commit.author.name}</OVERRIDEN>'
        return orig_commit

    def __iter__(self):
        for commit in self.compute_path():
            yield commit

    def compute_path(self, include_merge_commits=False) -> Deque[str]:
        """
        Compute the path from <current_commit_hash> to <historical_commit_hash> in the <repo>
        :return: A list of commit hashes sorted from <current_commit_hash> to <historical_commit_hash>
        """
        c_range = f"{self.head}...{self.hist}"
        args = ["--topo-order", "--ancestry-path", "--reverse"]
        # if not include_merge_commits:
        #     args.append("--no-merges")
        output = self.repo.git.execute(["git", "rev-list", *args, c_range])
        assert isinstance(output, str)
        ret = deque(output.splitlines())
        ret.insert(0, self.hist)
        return ret

    def checkout_file_from(self, commit_hash: str, file_name: str) -> str:
        """
        Checkout the file <file_name> from the parent of the commit with the hash <commit_hash>
        :param commit_hash:
        :param file_name:
        :return:
        """
        result = self.repo.git.execute(['git', 'show', f'{commit_hash}:{str(file_name)}'])
        assert isinstance(result, str)
        return result

    def populate_previously_unseen_file(self, config: Optional[Configuration], change: 'Change', commit_hash: str,
                                        file_name: Path,
                                        ret: Dict[Path, 'Ownership'], commit_date: datetime.datetime) -> None:
        file_path = posix_repo_p(str(file_name), self.repo)
        # Obtain the previous version of the file as a base
        content = self.checkout_file_from(commit_hash, file_path)
        ret[file_name] = Ownership(file_name, len(content.splitlines(keepends=True)),
                                   content, commit_date, commit_hash, '?')
        if config is not None and config.blame_unseen:
            ret[file_name].fix_file(self.repo, commit_hash, commit_date)
        ret[file_name].apply_change(change.hunks, commit_hash, self.repo, change.author, commit_date)

    def analyze(self, config: Optional[Configuration] = None, verbose=False) -> AnalysisResult:
        """
        Analyze the repository <repo> from the commit with the hash <historical_commit_hash> to the commit with the hash
        <current_commit_hash>
        :return:
        """
        path = self.compute_path()

        ret: Dict[Path, Ownership] = {}

        index = 1
        for commit_hash in path:
            if verbose:
                print(f"{INFO} Analyzing commit {commit_hash} ({index}/{len(path)})")
                index += 1
            commit_date = self.commit(commit_hash).committed_datetime
            file_ownership = get_file_changes(self, commit_hash, self.repo)
            for file_name, change in file_ownership.items():
                if file_name not in ret:
                    if change.hunks and change.hunks[0].mode == 'R':
                        assert change.previous_name is not None
                        if change.previous_name in ret:
                            ret[file_name] = ret[change.previous_name]
                            ret[file_name].file = file_name
                            del ret[change.previous_name]
                        else:
                            self.populate_previously_unseen_file(config, change, commit_hash, file_name, ret, commit_date)
                        ret[file_name].apply_change(change.hunks, commit_hash, self.repo, change.author, commit_date)
                    elif change.hunks and change.hunks[0].mode == 'A':
                        ret[file_name] = Ownership(file_name, change.hunks[0].change_end, change.hunks[0].content,
                                                   commit_date, commit_hash, change.author)
                    elif not change.hunks:
                        # This is a binary file or empty file
                        ret[file_name] = Ownership(file_name, -1, '', commit_date, commit_hash, change.author)
                    elif change.hunks[0].mode == 'M':
                        # This file already existed in the repo, this can occur if the analysis does not
                        # start from the first commit
                        self.populate_previously_unseen_file(config, change, commit_hash, file_name, ret, commit_date)
                    continue

                elif file_name in ret and change.hunks and change.hunks[0].mode == 'A' and not ret[file_name].exists:
                    # This file was deleted in a previous commit and re-added in this commit
                    ret[file_name].exists = True
                    hunk = change.hunks[0]
                    split = hunk.content.splitlines(keepends=True)
                    Ownership.fix_length(hunk, split)

                    for l in range(1, hunk.new_len + 1):
                        content_index = hunk.change_start - 1 + hunk.new_len - l
                        text = split[content_index]
                        ret[file_name].changes.insert(hunk.prev_start, LineMetadata(change.author, text, commit_date))
                    ret[file_name].line_count = hunk.new_len
                    ret[file_name].history[commit_hash] = OwnershipHistory(commit_hash, ret[file_name].changes,
                                                                           change.hunks[0].change_end)
                    continue

                elif file_name in ret and change.hunks and change.hunks[0].mode == 'D':
                    ret[file_name].delete(commit_hash)
                    continue

                if len(change.hunks) == 1 and change.hunks[0].mode == 'D':
                    continue

                if len(change.hunks) == 1 and change.hunks[0].mode == 'A':
                    # This file was added in a previous commit as well as in this commit
                    # Likely a conflict down the line
                    if verbose:
                        print(f"{WARN} File {file_name} was added in a previous commit as well as in this commit.")
                        print(f"{INFO} Replacing... (This may lead to a loss of information)")
                        print(f"{INFO} One cause for this is Windows NTFS being case insensitive. "
                              f"Or a merge conflict will happen.")
                        ret[file_name] = Ownership(file_name, change.hunks[0].change_end, change.hunks[0].content,
                                                   commit_date, commit_hash, change.author)
                        print()
                    continue

                ret[file_name].apply_change(change.hunks, commit_hash, self.repo, change.author, commit_date)

        if verbose:
            print()
            print(f"{SUCCESS} Analyzed {len(ret)} files.")

        lstree = self.repo.git.execute(['git', 'ls-tree', '-r', self.head, '--name-only'])
        assert isinstance(lstree, str)

        files = lstree.splitlines()
        print(f"{INFO} Found {len(files)} files in the repository. {len(ret)} files were analyzed.")
        if len(ret) > len(files):
            print(f"{INFO} More were analyzed due to renames and deletes. "
                  f"If a file was marked as renamed, the ownership was transferred to the new file correctly.")

        return ret

    def find_unmerged_branches(self, end_date: Optional[float] = None) -> List[Tuple[str,List[str]]]:
        """
        Find all unmerged branches in the repository <repo>
        :return: A list of all unmerged branches
        """
        main_path = self.compute_path(include_merge_commits=True)

        head_date = end_date if end_date is not None else self.commit(self.head).committed_date
        hist_date = self.commit(self.hist).committed_date

        reversed_path = list(main_path)
        reversed_path.reverse()

        result = self.repo.git.execute(["git", "log", "--format=%H", "--all"])
        assert isinstance(result, str)
        all_commits = result.splitlines()

        all_in_range = []
        for commit in all_commits:
            c = self.commit(commit)
            if c.committed_date <= head_date and c.committed_date >= hist_date:
                all_in_range.append(commit)

        all_set = set(all_in_range)
        unmerged_commits = all_set.difference(main_path)

        ret: List[Tuple[str, List[str]]] = []

        starting_points = [x for x in unmerged_commits if x in self.marked_commits]

        outside_range = False
        for commit in starting_points:
            if self.repo.commit(commit).committed_datetime < self.hist_commit.committed_datetime or \
                    self.repo.commit(commit).committed_datetime > self.head_commit.committed_datetime:
                # This commit is not in the range of the analysis
                continue
            path = []
            identifier = self.marked_commits[commit]
            current = commit
            while current is not None and current not in main_path and not outside_range:
                path.append(current)
                current = self.repo.commit(current).parents[0].hexsha
                if self.repo.commit(current).committed_datetime < self.hist_commit.committed_datetime or \
                        self.repo.commit(current).committed_datetime > self.head_commit.committed_datetime:
                    # This commit is not in the range of the analysis
                    outside_range = True
            path.append(current)
            ret.append((identifier, path))

        return ret

    def unmerged_commits_info(self, repository: Repo, config: Configuration, contributors: List[Contributor]) -> None:
        end_date = (self.head_commit.committed_datetime + timedelta(days=1)).timestamp()
        unmerged_content = self.find_unmerged_branches(end_date)
        for branch, commits in unmerged_content:
            print()
            print(f'{WARN} Unmerged branch: {branch}')
            not_first = False

            for commit in commits:
                if not_first:
                    print(f'{(" " * 19)}{DOWN_ARROW}{(" " * 19)}')
                not_first = True
                commit_inst = repository.commit(commit)
                author = commit_inst.author.name
                assert isinstance(author, str)
                contrib = find_contributor(contributors, author)
                if contrib is None:
                    contrib = Contributor.unknown()
                commit_header = str(commit_inst.message.splitlines()[0])

                print(commit + f" ({COMMIT} Commit: {commit_header} by '{contrib.name}')")
        if not unmerged_content:
            print(f'{SUCCESS} No unmerged branches found! Everything is in the "{config.default_branch}" branch!')


class FileSection:
    def __init__(self, prev_start: int, prev_len: int, change_start: int, change_len: int,
                 content: str, prev_file_hexsha: bytes, mode: Optional[str]):
        self.prev_start = prev_start
        self.prev_end = prev_start + prev_len
        self.prev_len = prev_len
        self.change_start = change_start
        self.change_end = change_start + change_len
        self.new_len = change_len
        self.length_difference = change_len - prev_len
        self.prev_file_hexsha = prev_file_hexsha
        self.content = content
        self.mode = mode

    def __repr__(self):
        return f"FileSection(prev={self.prev_start}-{self.prev_end} ({self.prev_len}), " \
               f"change={self.change_start}-{self.change_end} ({self.new_len}), " \
               f"prev_file_hexsha={self.prev_file_hexsha}, mode={self.mode})"


class Change:
    def __init__(self, author: str) -> None:
        self.hunks: List[FileSection] = []
        self.author = author
        self.previous_name: Optional[Path] = None
        self.is_binary = False

    def add_hunk(self, prev_start: int, prev_len: int, change_start: int, change_len: int,
                 content: str,
                 previous_file_hexsha: bytes, mode: Optional[str] = None) -> None:
        self.hunks.append(
            FileSection(prev_start, prev_len, change_start, change_len, content, previous_file_hexsha, mode))


class Ownership:
    def __init__(self, file: Path, init_line_count: int, initial_content: str, first_date: datetime.datetime,
                 commit_hash: str, author: str = '') -> None:
        self.file = file
        self.history: Dict[str, OwnershipHistory] = {}
        split = initial_content.splitlines(keepends=True)
        if split:
            has_newline = split[-1].endswith('\n')
            if not has_newline:
                init_line_count -= 1
            else:
                split.append('')
        else:
            pass
            # Empty file or binary file
        self.changes: List[LineMetadata] = [LineMetadata(author, split[i], first_date) for i in range(init_line_count)]
        if not self.changes or init_line_count == -1:
            # Empty file or binary file
            self.changes = [LineMetadata(author, '', first_date)]
        self.line_count = init_line_count  # Lines are indexes starting with 1
        self.exists = True

        self.history[commit_hash] = OwnershipHistory(commit_hash, copy.deepcopy(self.changes), init_line_count)

    @property
    def content(self):
        return ''.join(map(lambda x: x.content, self.changes))

    def delete(self, commit_hash: str):
        self.history[commit_hash] = OwnershipHistory(commit_hash, copy.deepcopy(self.changes), self.line_count)
        self.changes = []
        self._line_count = 0
        self.exists = False

    def fix_file(self, repo: Repo, commit_hash: str, date: datetime.datetime) -> None:
        blame_res = repo.blame(commit_hash, posix_repo_p(str(self.file), repo))
        assert blame_res is not None
        self.changes = []
        for section in blame_res:
            commit = section[0]
            assert isinstance(commit, Commit)
            lines = section[1]
            assert isinstance(lines, list)
            self.changes.extend([LineMetadata(commit.author.name, str(line), date) for line in lines])
            self.line_count = len(self.changes)

    def apply_change(self, hunks: List[FileSection], commit_hash: str, repo: Repo,
                     author: AuthorName, date: datetime.datetime) -> None:
        assert not any(map(lambda x: x.mode in ['A', 'D'], hunks)), \
            "This function can only be used to add changes to existing files."

        if self.line_count == -1:
            # This is a binary file
            self.changes[0] = LineMetadata(author, '\1', date)
            return

        new_file_index_offset = 0
        abs_changes = 0

        for hunk in hunks:
            if hunk.mode == 'CONFLICT':
                self._apply_conflict_resolution(author, hunk, date)
                abs_changes += hunk.length_difference
                continue

            if hunk.prev_len == 0:
                # This is an addition
                split = hunk.content.splitlines(keepends=True)
                self.fix_length(hunk, split)

                for l in range(1, hunk.new_len + 1):
                    index = hunk.change_start - 1 + hunk.new_len - l
                    text = split[index]
                    self.changes.insert(hunk.prev_start + new_file_index_offset,
                                        LineMetadata(author, text, date))
                new_file_index_offset += hunk.new_len
                abs_changes += hunk.new_len
                self.line_count += hunk.new_len
            elif hunk.new_len == 0:
                # This is a deletion
                for _ in range(hunk.prev_len):
                    try:
                        self.changes.pop(hunk.change_start)
                    except IndexError:
                        self.fix_file(repo, commit_hash, date)

                new_file_index_offset -= hunk.prev_len
                abs_changes += hunk.prev_len
                self.line_count -= hunk.prev_len
            else:
                split = hunk.content.splitlines(keepends=True)
                self.fix_length(hunk, split)
                # This is a change
                new_meta = [LineMetadata(author, split[hunk.change_start - 1 + i], date) for i in range(hunk.new_len)]
                file_start = hunk.prev_start - 1 + new_file_index_offset
                prev_line_authors = []
                for i in range(hunk.prev_len):
                    try:
                        prev_line_authors.append((self.changes[file_start].author, self.changes[file_start].content))
                        self.changes.pop(file_start)
                    except IndexError:
                        self.fix_file(repo, commit_hash, date)
                for i in range(hunk.new_len):
                    if hunk.new_len - 1 - i < len(prev_line_authors) and \
                            new_meta[hunk.new_len - 1 - i].content.strip() == \
                            prev_line_authors[hunk.new_len - 1 - i][1].strip():
                        new_meta[hunk.new_len - 1 - i].author = prev_line_authors[hunk.new_len - 1 - i][0]
                    self.changes.insert(file_start, new_meta[hunk.new_len - 1 - i])
                new_file_index_offset += hunk.length_difference
                abs_changes += hunk.length_difference
                self.line_count += hunk.length_difference

        self.history[commit_hash] = OwnershipHistory(commit_hash, copy.deepcopy(self.changes), abs_changes)

    def _apply_conflict_resolution(self, author: str, hunk: FileSection, date: datetime.datetime):
        split = hunk.content.splitlines(keepends=True)
        init_line_count = len(split)
        if split:
            has_newline = split[-1].endswith('\n')
            if not has_newline:
                init_line_count -= 1
            else:
                split.append('')
        else:
            pass
            # Empty file or binary file
        self.changes = [LineMetadata(author, split[i], date) for i in range(init_line_count)]
        self._line_count = init_line_count

    @staticmethod
    def fix_length(hunk, split):
        has_newline = split[-1].endswith('\n')
        had_newline = hunk.content.endswith('\n')
        if not has_newline and hunk.change_end == len(split) and had_newline:
            hunk.new_len -= 1
        elif has_newline and hunk.change_end == len(split) and not had_newline:
            split.append('')

    def __str__(self):
        return f"Ownership(lines={self.line_count}, changes={self.changes})"


def get_file_changes(commit_range: CommitRange, commit_hash: str, repo: Repo) -> Dict[Path, Change]:
    """
    Get the ownership of each file in the commit with the hash <commit_hash>
    :param commit_hash: The hash of the commit to analyze
    :param repo: The repository to analyze
    :return: A dictionary mapping each file name to the lines changed by the author of the commit
    """
    commit = commit_range.commit(commit_hash)

    if commit.parents:
        if len(commit.parents) == 2:
            # This is a merge commit
            result = repo.git.execute(['git', 'show', commit_hash, "--cc", "--unified=0"])
            assert isinstance(result, str)
            matches = HUNK_CONFLICT_PATTERN.findall(result)  # TODO
            a_names = CONFLICT_A_NAME.findall(result)  # TODO
            b_names = CONFLICT_B_NAME.findall(result)
            ret = {}
            for i in range(len(b_names)):
                try:
                    content = repo.git.execute(['git', 'show', f'{commit_hash}:{b_names[i]}'])
                    assert isinstance(content, str)
                except Exception as e:
                    content = None
                    print(f"{WARN} There is a conflict and the resolved file could not be read! Commit: {commit_hash}.")
                    print(f"{WARN} This file will be marked as binary.")
                    print(f"{WARN} Exception: {e}")
                    print()

                change = Change(commit.author.name)
                actual_path = Path(repo_p(b_names[i], repo))
                ret[actual_path] = change
                if content is None:
                    change.is_binary = True
                else:
                    print(f"{WARN} There is a conflict in file {actual_path}. Commit: {commit_hash}.")
                    print(f"{INFO} It appears to be resolvable... however, "
                          f"ownership will be transferred to the author of this commit.")
                    print()

                change.add_hunk(0, 0, 0, 0, content, b"", "CONFLICT")
            return ret
        elif len(commit.parents) == 1:
            # This is a linear commit
            d = commit.parents[0].diff(commit, create_patch=True, unified=0)
        else:
            print(f"{WARN} Octopus merge detected: {len(commit.parents)} parents for commit {commit_hash}.")
            print(f"{WARN} This is unfortunately not supported. This commit will hold no diffs.")
            d = DiffIndex()
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
        actual_path = repo_p(diff.b_path, repo) if diff.b_path is not None else repo_p(diff.a_path, repo)

        if diff.b_path is None:
            ret[actual_path] = Change(author)
            mode = "D"
        else:
            ret[actual_path] = Change(author)
            mode = "A" if diff.new_file else "M"
        if diff.renamed:
            mode = "R"
            ret[actual_path].previous_name = repo_p(diff.a_path, repo)
        try:
            content = diff.b_blob.data_stream.read().decode('latin-1') if diff.b_blob is not None else \
                diff.a_blob.data_stream.read().decode('latin-1')
        except Exception as e:
            content = None
            if not diff.renamed:
                print(f"{WARN} Could not read content of {actual_path} in commit {commit_hash}.")
                print(f"{WARN} This file will be marked as binary.")
                print(f"{WARN} Exception: {e}")
        for match in matches:
            prev_line_start, prev_line_len, line_start, line_len = match
            change_start = int(line_start)
            change_len = int(line_len) if line_len != '' else 1
            prev_start = int(prev_line_start)
            prev_len = int(prev_line_len) if prev_line_len != '' else 1
            ret[actual_path].add_hunk(prev_start, prev_len, change_start, change_len, content,
                                      diff.a_blob.hexsha if diff.a_blob is not None else diff.b_blob.hexsha, mode)
        if not matches and not diff.renamed:
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
        for line_meta in val.changes[1:]:
            contributor = find_contributor(contributors, line_meta.author)
            if contributor is not None:
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
            for parent in repo.commit(curr).parents:  # This can be from repo directly
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
