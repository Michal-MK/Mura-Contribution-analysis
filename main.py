import os
import pathlib
from typing import Set, Dict, List

import git

from lib import file_contents, first_commit, set_repo, commit_summary, stats_for_contributor, get_files_with_flag

repos_path = "C:\\MUNI\\xth. semester\\sdipr\src\\repositories"
single_commit = repos_path + "\\single_commit"
tg = "C:\\Repositories\\TurtleGraphics"


# https://stackoverflow.com/questions/2472221/how-to-check-if-a-file-contains-plain-text
def is_binay_file(filepathname):
    textchars = bytearray([7, 8, 9, 10, 12, 13, 27]) + bytearray(range(0x20, 0x7f)) + bytearray(range(0x80, 0x100))
    is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))

    if is_binary_string(open(filepathname, 'rb').read(1024)):
        return True
    else:
        return False


class GitFile:
    def __init__(self, path: str):
        self.path = path
        self.is_text = not is_binay_file(path)


class ContribRange:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end


repo = git.Repo(tg)
set_repo(repo)

contributors: Set[str] = set()

for commit in repo.iter_commits():
    contributors.add(commit.author.name if commit.author.name else "Unknown")

print(f"Contributors: {contributors}")

for contributor in contributors:
    # stats_for_contributor(contributor)
    pass

current = head = repo.commit('HEAD')
first_commit = first_commit(head)

added = get_files_with_flag(current, flag="A")
delet = get_files_with_flag(current, flag="D")
renam = get_files_with_flag(current, flag="R")
modif = get_files_with_flag(current, flag="M")

# while first_commit != current:
#     commit_summary(current)
#     if not current.parents:
#         print("HEAD is not based from first commit!")
#     current = current.parents[0]

# commit_summary(current)

code_owners: Dict[GitFile, List[ContribRange]] = {}

last_commit = repo.commit('2dee9480a4d9aff4c006467d4c4a61b7ff7b9871')
start_commit = repo.commit('2dee9480a4d9aff4c006467d4c4a61b7ff7b9871~20')

print("Iterating through commits")
commits_to_consider = []
for commit in repo.iter_commits():
    commits_to_consider.append(commit)
    if commit == start_commit:
        break

for c in reversed(commits_to_consider):
    print(f"Commit: {c.committed_date}")
    print(f"{c.message.encode('utf-8')}")

repo.git.checkout(start_commit, force=True)


def print_dir_tree(path: str, level: int):
    for file in os.listdir(path):
        if repo.ignored(fsi):
            print(f"ignored: {file}")
            continue
        # print(f"{'  ' * level}{file}")
        if os.path.isdir(os.path.join(path, file)):
            print_dir_tree(os.path.join(path, file), level + 1)

ignored_list = []

os.chdir(tg)
for fsi in os.listdir('.'):
    if fsi == '.git':
        continue
    if pathlib.Path(fsi).is_dir():
        os.chdir(fsi)
        if repo.ignored(fsi):
            print(f"ignored: {fsi}")
            continue
        print_dir_tree(fsi, 0)
# IN:
# # of commits
# # of additions/changes/deletions
# "Code ownership"
#  - # of lines added by contributor 100% ownership
#  - # of lines modified by contributor % of line -> % ownership
# timestamp of a commit
# rules
#
