from pathlib import Path
from typing import Any, TYPE_CHECKING

from git import Repo

import lib
import repository_hooks
from uni_chars import *

if TYPE_CHECKING:
    from configuration import Configuration


def parse_model_content(model: Any, file: Path) -> Any:
    with open(file) as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue

            trimmed = line.strip()
            split = trimmed.split('=')
            key = split[0].strip()
            value = float(split[1].strip())

            model.__dict__[key] = value

    return model


def validate_repository(repository_path: str, config: 'Configuration') -> Repo:
    path = Path(repository_path)
    if not path.exists():
        raise FileNotFoundError(f"Path {path} does not exist")
    if not path.is_dir():
        raise NotADirectoryError(f"Path {path} is not a directory")

    try:
        repo = Repo(path)
        print(f"{SUCCESS} Repository path '{path}' points to a repository")

        if config.ignore_remote_repo:
            print(f"{INFO} Skipping remote repositories as 'config.ignore_remote_repo = True'")
            return repo

        url = repo.remotes[config.default_remote_name].url
        remote = repository_hooks.parse_project(url, gitlab_access_token=config.gitlab_access_token,
                                                     github_access_token=config.github_access_token)

        print(f"{INFO} Remote repository found: {url} ({remote.__class__.__name__})")

        if isinstance(remote, repository_hooks.GitLabRepository):
            print(f"{SUCCESS} GitLab access token validated successfully!")

        if isinstance(remote, repository_hooks.GithubRepository):
            print(f"{SUCCESS} GitHub access token validated successfully!")

        return repo
    except Exception as e:
        raise ValueError(f"Path {path} is not a git repository") from e


def validate_rules():
    return None