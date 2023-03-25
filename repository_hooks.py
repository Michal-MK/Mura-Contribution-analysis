from __future__ import annotations

import abc
import datetime
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

import gitlab
import urllib3.util

if TYPE_CHECKING:
    from configuration import Configuration


class Issue:
    def __init__(self, name: str, description: str, state: str, created_at: datetime.datetime,
                 closed_at: Optional[datetime.datetime], author: str, closed_by: str, assigned_to: str):
        self.name = name
        self.description = description
        self.state = state
        self.created_at = created_at
        self.closed_at = closed_at
        self.author = author
        self.closed_by = closed_by
        self.assigned_to = assigned_to


class PR:
    def __init__(self, name: str, description: str, created_at: datetime.datetime,
                 merged_at: Optional[datetime.datetime], author: str,
                 merged_by: str, commit_shas: List[str], reviewers: List[str],
                 target_branch: str, source_branch: str):
        self.name = name
        self.description = description
        self.created_at = created_at
        self.merged_at = merged_at
        self.merged_by = merged_by
        self.author = author
        self.commit_shas = commit_shas
        self.reviewers = reviewers
        self.target_branch = target_branch
        self.source_branch = source_branch


class RemoteRepository:
    def __init__(self, project_path: str, access_token: str):
        self.url = project_path
        self.access_token = access_token
        self.host = "https://github.com"

    @abc.abstractmethod
    def get_issues(self) -> List[Issue]:
        pass

    @abc.abstractmethod
    def get_pull_requests(self) -> List[PR]:
        pass

    @abc.abstractmethod
    def get_members(self) -> List[str]:
        pass


class GitLabRepository(RemoteRepository):
    def __init__(self, host: str, project_path: str, access_token: str):
        super().__init__(project_path, access_token)
        self.host = host
        self.connection = gitlab.Gitlab(host, private_token=access_token)
        self.connection.auth()
        self.project = self.connection.projects.get(project_path, lazy=False)

    def get_issues(self) -> List[Issue]:
        return [Issue(name=x.title,
                      description=x.description,
                      created_at=x.created_at,
                      closed_at=x.closed_at,
                      state=x.state,
                      closed_by=x.closed_by['name'],
                      author=x.author['name'],
                      assigned_to=x.assignee['name'])
                for x in self.project.issues.list(iterator=True)]

    def get_pull_requests(self) -> List[PR]:
        return [PR(name=x.title,
                   description=x.description,
                   created_at=x.created_at,
                   merged_at=x.merged_at,
                   merged_by=x.merged_by['name'],
                   author=x.author['name'],
                   commit_shas=[c['id'] for c in x.commits()],
                   reviewers=[r['name'] for r in x.reviewers],
                   target_branch=x.target_branch,
                   source_branch=x.source_branch)
                for x in self.project.mergerequests.list(iterator=True)]

    def get_members(self) -> List[str]:
        return [x.name for x in self.project.members.list(iterator=True)]


class GithubRepository(RemoteRepository):
    def __init__(self, project_path: str, access_token: str):
        super().__init__(project_path, access_token)

    # Github is not supported in the final version


def parse_projects(projects_path: Path, access_token: str) -> List[RemoteRepository]:
    projects = []
    if not projects_path.exists():
        raise FileNotFoundError(f"Projects file not found at {projects_path.absolute()}")
    with open(projects_path, 'r') as f:
        for line in f.readlines():
            if not line.strip() or line.startswith('#'):
                continue
            projects.append(line.strip())
    repos: List[RemoteRepository] = []
    for project in projects:
        uri = urllib3.util.parse_url(project)
        if "gitlab" in uri.host:
            repos.append(GitLabRepository(uri.scheme + '://' + uri.host, uri.path[1:], access_token))
        if "github" in uri.host:
            repos.append(GithubRepository(uri.path, access_token))
    return repos
