from __future__ import annotations

import os
import typing
from pathlib import Path
from typing import Union, List, Optional, Literal, Set, Dict, Tuple, DefaultDict

from git import Repo, Commit


if typing.TYPE_CHECKING:
    from configuration import Configuration
    from history_analyzer import CommitRange

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


def commit_summary(commit: Commit) -> None:
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


def get_tracked_files(project_root: Union[Path, Repo]) -> List[FileGroup]:
    """
    Find all files that are related, relative to the project root
    :
    :param project_root: The root directory of the project
    :return: A dictionary of all directories and their files which are related to each other
    """
    ret: List[FileGroup] = []

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


def repo_p(file_name: str):
    return Path(os.path.join(REPO.common_dir, '..', file_name)).resolve()


class Contributor:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
        self.aliases: List['Contributor'] = []

    def __eq__(self, other):
        return isinstance(other, Contributor) and other.name == self.name and other.email == self.email

    def __hash__(self):
        return hash(self.name) + hash(self.email)

    def __str__(self):
        return f"{self.name} <{self.email}> ({[str(a) for a in self.aliases]})"

    def __repr__(self):
        return self.__str__()


class Percentage:
    # Tuple[Dict[str, List[Tuple[str, float]]], Dict[str, float]]:
    def __init__(self, file_per_contributor: Dict[Path, List[Tuple[str, float]]],
                 global_contribution: DefaultDict[str, float]):
        self.file_per_contributor = file_per_contributor
        self.global_contribution = global_contribution


def get_contributors(range:Optional[CommitRange]=None, match_on_name=True, match_on_email=True) -> List[Contributor]:
    """
    Get a list of all contributors

    :return: A list of all contributors
    """
    contributors: Set[Contributor] = set()
    if range is not None:
        commits = [REPO.commit(x) for x in range]
    else:
        commits = [x for x in REPO.iter_commits()]

    for commit in commits:
        contributors.add(Contributor(commit.author.name, commit.author.email))

    matched_contributors: List[Contributor] = []
    for it in contributors:
        matched = False
        for other in matched_contributors:
            if it.name == other.name and it.email == other.email:
                continue
            if it.name == other.name or it.email == other.email and (match_on_name and match_on_email):
                other.aliases.append(it)
                matched = True
                break
            if it.name == other.name and match_on_name and not match_on_email:
                other.aliases.append(it)
                matched = True
                break
            if it.email == other.email and match_on_email and not match_on_name:
                other.aliases.append(it)
                matched = True
                break

        if not matched:
            matched_contributors.append(it)
    return matched_contributors


def find_contributor(contributors: List[Contributor], author: str) -> Contributor:
    for contributor in contributors:
        if author == contributor.name:
            return contributor
        if author in contributor.aliases:
            return contributor
        if author in list(map(lambda x: x.name, contributor.aliases)):
            return contributor
    raise ValueError('Contributor not found')


class ContributionDistribution:
    def __init__(self, file: str, percentage: float):
        self.file = file
        self.percentage = percentage

    def __iter__(self):
        yield self.file
        yield self.percentage

    def __str__(self):
        return f"{os.path.relpath(self.file, REPO.working_dir)} ({self.percentage})"


def compute_file_ownership(percentage: Percentage, contributors: List[Contributor], config: Configuration) \
        -> Dict[Contributor, List[ContributionDistribution]]:
    ret: Dict[Contributor, List[ContributionDistribution]] = {}
    for file, percentages in percentage.file_per_contributor.items():
        for contributor, contrib_percent in percentages:
            if contributor == '' or contributor == '_':
                # No author name comes from incomplete git history (starting from a certain commit)
                # Placeholder name '_' indicates 0 line index (no contribution) and trailing newline
                continue
            contrib = find_contributor(contributors, contributor)
            if contrib not in ret:
                ret[contrib] = []
            if contrib_percent > config.full_ownership_min_threshold:
                ret[contrib].append(ContributionDistribution(file, 1))
            elif contrib_percent < config.ownership_min_threshold:
                continue
            else:
                ret[contrib].append(ContributionDistribution(file, contrib_percent))
    return ret
