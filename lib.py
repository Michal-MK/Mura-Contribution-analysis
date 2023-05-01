from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Union, List, Optional, Set, Dict, Tuple, DefaultDict, Any, TYPE_CHECKING
from unidecode import unidecode

from git import Repo, Commit, Actor

from uni_chars import *

if TYPE_CHECKING:
    from configuration import Configuration
    from history_analyzer import CommitRange

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

    def __str__(self):
        return f"'{self.name}': {len(self.files)} files."

    def __repr__(self):
        return self.__str__()


def first_commit(commit: Commit) -> Commit:
    while commit.parents:
        commit = commit.parents[0]
    return commit


def commit_summary(commit: Commit) -> None:
    print(f"There are total of {commit.stats.total['files']} changed files")
    print(f"Author: {commit.author}")
    print(f"Message: {commit.message}")


def stats_for_contributor(contributor: Contributor, commit_range: CommitRange) -> Tuple[int, int]:
    insertions = 0
    deletions = 0
    for commit_sha in commit_range:
        commit = commit_range.commit(commit_sha)
        if contributor == commit.author and str(commit.hexsha) in commit_range:
            insertions += commit.stats.total['insertions']
            deletions += commit.stats.total['deletions']
    return insertions, deletions


class FlaggedFiles:
    def __init__(self):
        self.counts = {"A": 0, "R": 0, "D": 0, "M": 0}
        self.paths = {"A": [], "R": [], "D": [], "M": []}

    def update(self, flag: str, count: int, paths: List[Path]):
        self.counts[flag] += count
        self.paths[flag].extend(paths)


def get_files_with_flags(commit: Commit) -> Dict[str, List[Union[int, List[Any]]]]:
    flags = ["A", "R", "D", "M"]
    result: Dict[str, List[Union[int, List[Any]]]] = {flag: [0, []] for flag in flags}
    parent: Optional[Commit] = None
    if commit.parents:
        parent = commit.parents[0]

    if parent is None:
        result["A"] = [len(commit.tree.blobs), [Path(file.name) for file in commit.tree.blobs]]
        return result

    for diff in parent.diff(commit):
        if diff.change_type in flags:
            result[diff.change_type][0] += 1  # type: ignore
            result[diff.change_type][1].append(Path(diff.b_path))  # type: ignore
    return result


def get_flagged_files_by_contributor(commit_range: CommitRange, contributors: List[Contributor]) -> Dict[
    str, FlaggedFiles]:
    result = {}
    for commit_hexsha in commit_range:
        commit = commit_range.commit(commit_hexsha)
        author = commit.author
        contributor = next((c for c in contributors if c == author), None)
        if contributor is None:
            continue
        name = contributor.name
        if name not in result:
            result[name] = FlaggedFiles()
        flagged_files = get_files_with_flags(commit)
        for flag, (count, paths) in flagged_files.items():
            assert isinstance(count, int), f"Count is not an int: {count}, this is very much not expected... How?"
            assert isinstance(paths, list), f"Paths is not a list: {paths}, this is very much not expected... How?"
            result[name].update(flag, count, paths)
    return result


def try_checkout(repo: Repo, commit_hash: str, force: bool = False) -> None:
    try:
        repo.git.checkout(commit_hash, force=force)
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


def get_tracked_files(project_root: Union[Path, Repo], verbose=False) -> List[FileGroup]:
    """
    Find all files that are related, relative to the project root
    :
    :param project_root: The root directory of the project
    :return: A dictionary of all directories and their files which are related to each other
    """
    ret: List[FileGroup] = []

    if project_root is None:
        raise ValueError(f"{ERROR} No project_root specified! Did you execute all code blocks above?")

    if isinstance(project_root, Repo):
        repo_dir = project_root.working_dir
        assert repo_dir is not None
        project_root = Path(repo_dir)

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

    if verbose:
        print(f"{SUCCESS} Found {len(ret)} groups of related files.")

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


def posix_repo_p(file_name: str, repo: Repo) -> str:
    repo_dir = repo.working_dir
    assert repo_dir is not None
    if file_name.startswith(str(repo_dir)):
        return Path(os.path.relpath(file_name, repo_dir)).as_posix()
    return (Path(repo_dir) / file_name).resolve().as_posix()


def repo_p(file_name: str, repo: Repo) -> Path:
    repo_dir = repo.working_dir
    assert repo_dir is not None
    if file_name.startswith(str(repo_dir)):
        return Path(os.path.relpath(file_name, repo_dir))
    return Path((Path(repo_dir) / file_name).resolve())


class Contributor:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
        self.anonymized = False
        self.aliases: List['Contributor'] = []

    def contrib_equal(self, other: Union[Actor, Contributor]):
        return self.name == other.name or self.email == other.email or \
            any([a.contrib_equal(other) for a in self.aliases])

    def append_alias(self, contributor: Contributor):
        if contributor.name not in map(lambda s: s.name, self.aliases):
            self.aliases.append(contributor)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other or self.email == other or any([a.name == other for a in self.aliases])
        return self.contrib_equal(other)

    def __hash__(self):
        return hash(self.name) + hash(self.email)

    def __str__(self):
        if self.anonymized:
            return f"ANON: {self.name} <{self.email}>"
        return f"{self.name} <{self.email}> ({[str(a) for a in self.aliases]})"

    def __repr__(self):
        return self.__str__()

    @classmethod
    def unknown(cls):
        return Contributor('?', '?')

    @property
    def normalized(self) -> Contributor:
        return Contributor(unidecode(self.name), self.email)


class Percentage:
    # Tuple[Dict[str, List[Tuple[str, float]]], Dict[str, float]]:
    def __init__(self, file_per_contributor: Dict[Path, List[Tuple[Contributor, float]]],
                 global_contribution: DefaultDict[Contributor, float]):
        self.file_per_contributor = file_per_contributor
        self.global_contribution = global_contribution


def get_contributors(config: 'Configuration', commit_range: CommitRange, match_on_name=True,
                     match_on_email=True) -> List[Contributor]:
    """
    Get a list of all contributors

    :return: A list of all contributors
    """
    contributors: Set[Contributor] = set()
    commits = [commit_range.commit(x) for x in commit_range]

    for commit in commits:
        contributors.add(Contributor(commit.author.name, commit.author.email))

    matched_contributors: List[Contributor] = []
    for it in contributors:
        matched = False
        for other in matched_contributors:
            if it.name == other.name and it.email == other.email:
                continue
            if it.name == other.name or it.email == other.email and (match_on_name and match_on_email):
                other.append_alias(it)
                matched = True
                break
            if it.name == other.name and match_on_name and not match_on_email:
                other.append_alias(it)
                matched = True
                break
            if it.email == other.email and match_on_email and not match_on_name:
                other.append_alias(it)
                matched = True
                break
            if config.contributor_map is not None or config.contributor_map:
                for a, b in config.contributor_map:
                    if it.name == a and other.name == b or \
                            it.name == b and other.name == a:
                        other.append_alias(it)
                        matched = True
                        break
                    if it.name in [a, b]:
                        if a in map(lambda o: o.name, other.aliases) or \
                                b in map(lambda o: o.name, other.aliases):
                            matched = True
                            other.append_alias(it)
                            break
            if it.normalized in other.aliases:
                matched = True
                other.append_alias(it)
                break

        if not matched:
            it.append_alias(Contributor(unidecode(it.name), it.email))
            matched_contributors.append(it)

    if config.anonymous_mode:
        count = 1
        for contributor in matched_contributors:
            contributor.aliases.append(Contributor(contributor.name, contributor.email))
            contributor.name = f"Anonymous #{count}"
            contributor.email = f"contributor{count}@email.cz"
            contributor.anonymized = True
            count += 1

    matched_contributors.append(Contributor.unknown())

    return matched_contributors


def find_contributor(contributors: List[Contributor], author: str) -> Optional[Contributor]:
    for contributor in contributors:
        if author == contributor.name or author == contributor.email:
            return contributor
        if author in contributor.aliases:
            return contributor
        if author in list(map(lambda x: x.name, contributor.aliases)) or \
                author in list(map(lambda x: x.email, contributor.aliases)):
            return contributor
    return None


class ContributionDistribution:
    def __init__(self, file: Path, percentage: float, repo: Optional[Repo] = None):
        self.file = file
        self.percentage = percentage
        self.repo = repo

    def __iter__(self):
        yield self.file
        yield self.percentage

    def __str__(self):
        if self.repo is None:
            return f"{self.file} ({self.percentage})"
        return f"{repo_p(str(self.file), self.repo)} ({self.percentage})"


def compute_file_ownership(percentage: Percentage, config: Configuration, repo: Repo) \
        -> Dict[Contributor, List[ContributionDistribution]]:
    ret: Dict[Contributor, List[ContributionDistribution]] = defaultdict(list)
    for file, percentages in percentage.file_per_contributor.items():
        for contributor, contrib_percent in percentages:
            if contrib_percent > config.full_ownership_min_threshold:
                ret[contributor].append(ContributionDistribution(file, 1, repo))
            # elif contrib_percent < config.ownership_min_threshold:
            #     continue
            # else:
            #     ret[contributor].append(ContributionDistribution(file, contrib_percent))
    return ret
