'''
File responsible for interacting with remote repositories.
'''

from __future__ import annotations

import abc
import datetime
import os
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

import gitlab
import github
import urllib3.util

from uni_chars import *

if TYPE_CHECKING:
    from configuration import Configuration

DTF = "%Y-%m-%dT%H:%M:%S.%f%z"


class Issue:
    '''
    Data class representing an issue.
    '''

    def __init__(self, name: str, description: str, state: str, created_at: datetime.datetime,
                 closed_at: Optional[datetime.datetime], author: str, closed_by: str, assigned_to: str, url: str):
        self.name = name
        self.description = description
        self.state = state
        self.created_at = created_at
        self.closed_at = closed_at
        self.author = author
        self.closed_by = closed_by
        self.assigned_to = assigned_to
        self.url = url


class PR:
    '''
    Data class representing a pull request.
    '''

    def __init__(self, name: str, description: str, created_at: datetime.datetime,
                 merge_status: str, merged_at: Optional[datetime.datetime], author: str,
                 merged_by: str, commit_shas: List[str], reviewers: List[str],
                 target_branch: str, source_branch: str, url: str):
        self.name = name
        self.description = description
        self.created_at = created_at
        self.merge_status = merge_status
        self.merged_at = merged_at
        self.merged_by = merged_by
        self.author = author
        self.commit_shas = commit_shas
        self.reviewers = reviewers
        self.target_branch = target_branch
        self.source_branch = source_branch
        self.url = url


class RemoteRepository(abc.ABC):
    '''
    Abstract class representing a remote repository, such as GitHub or GitLab.
    '''

    def __init__(self, project_path: str, access_token: str):
        self.name: str = ''
        self.path = project_path
        self.access_token = access_token
        self.host = "https://github.com"
        self.pulls_cache: Optional[List[PR]] = None
        self.issue_cache: Optional[List[Issue]] = None
        self.members_cache: Optional[List[str]] = None

    @property
    @abc.abstractmethod
    def issues(self) -> List[Issue]:
        pass

    @property
    @abc.abstractmethod
    def pull_requests(self) -> List[PR]:
        pass

    @property
    @abc.abstractmethod
    def members(self) -> List[str]:
        pass


class GitLabRepository(RemoteRepository):
    def __init__(self, host: str, project_path: str, access_token: str):
        super().__init__(project_path, access_token)
        self.host = host
        try:
            self.connection = gitlab.Gitlab(host, private_token=access_token)
            self.connection.auth()
        except Exception as e:
            print(f"{ERROR} Could not connect to GitLab instance at {host}, check your access token.")
            print(f"{ERROR} {e}")
            print(f"{ERROR} This is fatal -> Exiting...")
            exit(1)

        if project_path.startswith("/"):
            project_path = project_path[1:]
        if project_path.endswith(".git"):
            project_path = project_path[:-4]
        if project_path.endswith("/"):
            project_path = project_path[:-1]
        self.project = self.connection.projects.get(project_path, lazy=False)
        self.name = self.project.name

    @property
    def issues(self) -> List[Issue]:
        if self.issue_cache is not None:
            return self.issue_cache
        var = self.project.issues.list(iterator=True)
        self.issue_cache = [Issue(name=x.title,
                                  description=x.description,
                                  created_at=datetime.datetime.strptime(x.created_at, DTF),
                                  closed_at=datetime.datetime.strptime(x.closed_at,
                                                                       DTF) if x.closed_at is not None else None,
                                  state=x.state,
                                  closed_by=x.attributes['closed_by']['name'] if x.state == 'closed' else '',
                                  author=x.author['name'],
                                  assigned_to=x.assignee['name'] if x.assignee is not None else '',
                                  url=x.web_url)
                            for x in var]
        return self.issue_cache

    @property
    def pull_requests(self) -> List[PR]:
        if self.pulls_cache is not None:
            return self.pulls_cache
        var = self.project.mergerequests.list(iterator=True)
        self.pulls_cache = [PR(name=x.title,
                               description=x.description,
                               created_at=datetime.datetime.strptime(x.created_at, DTF),
                               merge_status=x.merge_status,
                               merged_at=datetime.datetime.strptime(x.merged_at,
                                                                    DTF) if x.merged_at is not None else None,
                               merged_by=x.merged_by['name'] if x.merged_at is not None else '',
                               author=x.author['name'],
                               commit_shas=[c.id for c in x.commits()],
                               reviewers=[r['name'] for r in x.reviewers],
                               target_branch=x.target_branch,
                               source_branch=x.source_branch,
                               url=x.web_url)
                            for x in var]
        return self.pulls_cache

    @property
    def members(self) -> List[str]:
        if self.members_cache is not None:
            return self.members_cache
        self.members_cache = [x.name for x in self.project.members_all.list(iterator=True)]
        return self.members_cache


class GithubRepository(RemoteRepository):
    def __init__(self, project_path: str, access_token: str):
        if project_path.startswith("/"):
            project_path = project_path[1:]
        if project_path.endswith(".git"):
            project_path = project_path[:-4]
        super().__init__(project_path, access_token)

        try:
            self.connection = github.Github(access_token)
        except Exception as e:
            print(f"{ERROR} Could not connect to GitHub, check your access token.")
            print(f"{ERROR} {e}")
            print(f"{ERROR} This is fatal -> Exiting...")
            exit(1)

        self.project = self.connection.get_repo(project_path)
        self.name = self.project.name

    @property
    def issues(self) -> List[Issue]:
        if self.issue_cache is not None:
            return self.issue_cache
        var = self.project.get_issues()
        self.issue_cache = [Issue(name=x.title,
                                  description=x.body,
                                  created_at=x.created_at,
                                  closed_at=x.closed_at,
                                  state=x.state,
                                  closed_by=x.closed_by.login if x.closed_by is not None else '',
                                  author=x.user.login,
                                  assigned_to=x.assignee.login if x.assignee is not None else '',
                                  url=x.html_url)
                            for x in var]
        return self.issue_cache

    @property
    def pull_requests(self) -> List[PR]:
        if self.pulls_cache is not None:
            return self.pulls_cache
        var = self.project.get_pulls()
        self.pulls_cache = [PR(name=x.title,
                               description=x.body,
                               created_at=x.created_at,
                               merge_status=x.mergeable_state,
                               merged_at=x.merged_at,
                               merged_by=x.merged_by.login if x.merged_by is not None else '',
                               author=x.user.login,
                               commit_shas=[c.sha for c in x.get_commits()],
                               reviewers=[r.login for r in x.get_review_requests()[0]],
                               target_branch=x.base.ref,
                               source_branch=x.head.ref,
                               url=x.html_url)
                            for x in var]
        return self.pulls_cache

    @property
    def members(self) -> List[str]:
        if self.members_cache is not None:
            return self.members_cache
        self.members_cache = [x.name if x.name is not None else "" for x in self.project.get_contributors()]
        return self.members_cache


class DummyRepository(RemoteRepository):
    def __init__(self):
        super().__init__("", "")

    @property
    def issues(self) -> List[Issue]:
        return []

    @property
    def pull_requests(self) -> List[PR]:
        return []

    @property
    def members(self) -> List[str]:
        return []


def parse_project(project: str, gitlab_access_token: str, github_access_token: str) -> RemoteRepository:
    '''
    Parses a project url and returns a concrete implementation of RemoteRepository for the given host.
    Access tokens are required for GitLab and GitHub.
    '''
    uri = urllib3.util.parse_url(project)
    if "gitlab" in uri.host:
        return GitLabRepository(uri.scheme + '://' + uri.host, uri.path, gitlab_access_token)
    if "github" in uri.host:
        return GithubRepository(uri.path, github_access_token)
    raise ValueError(f"{ERROR} Unknown host {uri.host}")
