import math
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from time import sleep
from typing import Tuple, List, Dict, Optional, Any

import docker
import git
from git import Repo
from matplotlib import pyplot as plt
from matplotlib.dates import date2num, DateFormatter, drange
from sonarqube import SonarQubeClient
from sonarqube.utils.exceptions import AuthError

from configuration import Configuration, start_sonar
from history_analyzer import AnalysisResult, calculate_percentage, CommitRange
from lib import FileGroup, Contributor, get_contributors, compute_file_ownership, find_contributor, \
    stats_for_contributor, get_flagged_files_by_contributor, ContributionDistribution, Percentage, FlaggedFiles, repo_p
from remote_repository_weight_model import RemoteRepositoryWeightModel
from repository_hooks import parse_project, Issue
from semantic_analysis import LangElement
from semantic_weight_model import SemanticWeightModel

from pathlib import Path
from collections import defaultdict

from uni_chars import *

ContributorWeight = Dict[Contributor, float]
GlobalRuleWeightMultiplier = Dict[Contributor, float]


def build_tree(triples):
    tree = {}
    for triple in triples:
        current = tree
        for part in triple[0].parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[triple[2]] = current.get(triple[2], 0) + triple[1]
    return tree


def calculate_ownership(tree, ownership_cache=None):
    if ownership_cache is None:
        ownership_cache = {}
    if all(isinstance(value, float) for value in tree.values()):
        return tree
    ownership = defaultdict(float)
    count = 0
    for value in tree.values():
        if isinstance(value, dict):
            sub_ownership = calculate_ownership(value, ownership_cache)
            for owner, value in sub_ownership.items():
                ownership[owner] += value
            count += 1
    for owner in ownership:
        ownership[owner] /= count
    ownership_cache[id(tree)] = ownership
    return ownership


def get_owner(ownership: Dict[Contributor, List[ContributionDistribution]], file: Path) -> Optional[Contributor]:
    for k, v in ownership.items():
        if file in map(lambda x: x.file, v):
            return k
    return None


def print_tree(tree, level=0, prefix='', ownership_cache=None):
    if ownership_cache is None:
        ownership_cache = {}
    for i, (name, value) in enumerate(tree.items()):
        if i == len(tree) - 1:
            connector = '└── '
            new_prefix = prefix + '    '
        else:
            connector = '├── '
            new_prefix = prefix + '│   '
        if isinstance(value, dict):
            if all(isinstance(v, float) for v in value.values()):
                owners_str = ', '.join([f'{owner.name}: {value * 100:.0f}%' for owner, value in value.items()])
                print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
            else:
                sub_ownerships = [calculate_ownership(v, ownership_cache) for v in value.values() if
                                  isinstance(v, dict)]
                if len(sub_ownerships) > 0 \
                        and all(sub_ownerships[0] == sub_ownership for sub_ownership in sub_ownerships):
                    print(f'{prefix}{connector}{name}')
                else:
                    owners_str = ', '.join([f'{owner.name}: {value * 100:.0f}%' for owner, value in
                                            calculate_ownership(value, ownership_cache).items()])
                    print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
                print_tree(value, level + 1, new_prefix, ownership_cache)


def plot_commits(commits: List[str], commit_range: CommitRange, contributors: List[Contributor], repo: Repo,
                 force_x_axis_dense_labels=False) -> None:
    commit_data = defaultdict(list)
    min_date = datetime.max.replace(tzinfo=timezone.utc)
    max_date = datetime.min.replace(tzinfo=timezone.utc)

    for commit in commits:
        commit_obj = commit_range.commit(commit)
        for contributor in contributors:
            if contributor == commit_obj.author:
                committed_date = commit_obj.committed_datetime
                commit_data[contributor.name].append(date2num(committed_date))
                min_date = min(min_date, committed_date)
                max_date = max(max_date, committed_date)
                break

    plt.figure(figsize=(12, 6))

    for name, dates in commit_data.items():
        plt.plot_date(sorted(dates), range(len(dates)), label=name)
    plt.legend()
    plt.xticks(rotation=45)

    delta = timedelta(days=1)
    dates = drange(min_date, max_date, delta)

    if len(dates) <= 30 or force_x_axis_dense_labels:
        plt.gca().xaxis.set_major_formatter(DateFormatter('%b %d'))
        plt.gca().xaxis.set_tick_params(which='both', labelbottom=True)
        plt.xticks(dates)
    else:
        print(f"{INFO} Skipping x-axis labels for all {len(dates)} dates to avoid cluttering the x-axis.")
        print(f" - Set force_x_axis_labels to True to override this behavior.")

    plt.show()


def separator() -> None:
    print()
    print("============================================")
    print()


def header(text: str) -> None:
    print(text)
    print()


def display_contributor_info(commit_range: CommitRange, config: Configuration) -> List[Contributor]:
    contributors = get_contributors(config, commit_range=commit_range)
    header(f"{CONTRIBUTOR} Contributors:")

    for contrib in contributors:
        print(contrib)

    return contributors


def commit_info(commit_range: CommitRange, repo: Repo, contributors: List[Contributor]) \
        -> Tuple[Dict[Contributor, int], List[Tuple[Contributor, int, int]]]:
    header(f"{COMMIT} Total commits: {len(commit_range.compute_path())}")

    commit_distribution: Dict[Contributor, int] = defaultdict(lambda: 0)

    for commit in commit_range:
        author = commit_range.commit(commit).author.name
        if author is None:
            continue
        contributor = find_contributor(contributors, author)
        if contributor is None:
            print(f'{INFO} Autor {author} not found in contributors. Skipping commit.')
            continue
        commit_distribution[contributor] += 1
        split = repo.commit(commit).message.splitlines()
        message = split[0] if len(split) > 0 else ''
        print(f'Commit: {commit} - Msg: "{message}" by {CONTRIBUTOR} {contributor.name}')

    print()
    header(f"{COMMIT} Commits per contributor:")

    for contrib, count in commit_distribution.items():
        print(f"{count} commits by: {CONTRIBUTOR} {contrib}")

    insertions_deletions = []

    for contrib in contributors:
        insertion, deletion = stats_for_contributor(contrib, commit_range)
        print(f"{CONTRIBUTOR} {contrib.name}: inserted '{insertion}' lines and deleted '{deletion}' lines.")
        insertions_deletions.append((contrib, insertion, deletion))

    return commit_distribution, insertions_deletions


def insertions_deletions_info(insertions_deletions: List[Tuple[Contributor, int, int]]) -> None:
    insertions_deletions.sort(key=lambda x: x[1], reverse=True)

    contributor_names = [x[0].name for x in insertions_deletions]
    insertions = [x[1] for x in insertions_deletions]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    ax1.pie(insertions, labels=contributor_names, autopct='%1.1f%%')
    ax1.set_title('Insertions')

    # Sort data in descending order by deletions
    insertions_deletions.sort(key=lambda x: x[2], reverse=True)

    contributor_names = [x[0].name for x in insertions_deletions]
    deletions = [x[2] for x in insertions_deletions]

    ax2.pie(deletions, labels=contributor_names, autopct='%1.1f%%')
    ax2.set_title('Deletions')

    fig.subplots_adjust(wspace=0.5)

    plt.show()


def percentage_info(analysis_result: AnalysisResult, contributors: List[Contributor], config: Configuration) \
        -> Tuple[Percentage, Dict[Contributor, List[ContributionDistribution]]]:
    header(f'{PERCENTAGE} Percentage of tracked files:')

    percentage = calculate_percentage(contributors, analysis_result)

    for contributor_name, percent in percentage.global_contribution.items():
        print(f'\t{contributor_name}: {percent:.2%}')

    ownership = compute_file_ownership(percentage, config)

    for contributor, contribution in ownership.items():
        print(f"Files owned by {CONTRIBUTOR} {contributor.name}")
        for contrib_distribution in contribution:
            print(f"\t{contrib_distribution}")
        print(f"Total: {len(contribution)} for {CONTRIBUTOR} {contributor}")

    return percentage, ownership


def display_dir_tree(config: Configuration, percentage: Percentage, repo: Repo):
    header(f"{DIRECTORY_TREE} Dir Tree with ownership:")

    triples = []

    for key in percentage.file_per_contributor.keys():
        for name, percent in percentage.file_per_contributor[key]:
            triples.append((Path(os.path.relpath(key, repo.working_dir)), percent, name))

    tree = build_tree(triples)
    print_tree(tree)


def rule_info(config: Configuration, repo: Repo, ownership: Dict[Contributor, List[ContributionDistribution]],
              contributors: List[Contributor]) -> GlobalRuleWeightMultiplier:
    header(f"{RULES} Rules: ")

    ret: GlobalRuleWeightMultiplier = defaultdict(lambda: 1.0)

    for rule in config.parsed_rules.rules:
        print(rule)

    print()
    header(f"{VIOLATED_RULES} Violated Rules: ")

    rule_result = config.parsed_rules.matches(repo, ownership)

    for c, rules in rule_result.items():
        rules_format = [('\t' + str(rule) + os.linesep) for rule in rules]
        print(f"{ERROR} Contributor {c} did not fulfill the following requirements:")
        print("".join(rules_format), end='')
        ret[c] *= config.rule_violation_multiplier

    rule_set = set(config.parsed_rules.rules)
    for contrib in contributors:
        if contrib not in rule_result:
            rule_set = set()
            break
        rule_set = rule_set.intersection(rule_result[contrib])

    if rule_set:
        print()
        print(f"{WARN} The following rules were NOT fulfilled by all contributors:")
        for rule in rule_set:
            print(f"\t{rule}")
        print()
        print(f"Are the rules valid for the project?")

    return ret


def start_sonar_analysis(config: Configuration, repository_path: str) -> Optional[str]:
    if not config.use_sonarqube:
        print(f"{INFO} Syntax analysis uses SonarQube and 'config.use_sonarqube = False'. Skipping syntax analysis.")
        return None

    data_path, logs_path = start_sonar(config)

    print(f"{SUCCESS} SonarQube instance is starting...")
    if config.sonarqube_persistent:
        print(f"{INFO} SonarQube instance is persistent. "
              f"Data will be stored in '{data_path}' and logs in '{logs_path}'.")
    else:
        print(f"{INFO} SonarQube instance is not persistent. Data will be lost after the container is removed.")

    url = f'http://localhost:{config.sonarqube_port}'
    sonar = SonarQubeClient(sonarqube_url=url, username=config.sonarqube_login, password=config.sonarqube_password)

    response = ''
    while response != 'pong':
        sleep(2)
        try:
            response = sonar.system.ping_server()
        except AuthError as auth:
            print(f"{ERROR} Authentication failed. Please check your credentials. This is fatal.")
            print(f"{INFO} The defaults for new SonarQube instances are 'admin' for both username and password.")
            raise auth
        except Exception as e:
            print(f"{INFO} The container is still starting... this can take a second. "
                  f"If this is the first run. This can take a while depending on your internet connection.")
            pass

    ps = sonar.projects.search_projects()

    project: Optional[Any] = None
    project_key = ''
    for p in ps['components']:
        if p['name'] == repository_path:
            print(f"{INFO} Project '{repository_path}' already exists. Skipping creation.")
            project_key = p['key']
            project = p
            break

    if not project:
        project_key = uuid.uuid1().hex
        print(f"Creating project: {repository_path}. Key: {project_key}.")
        project = sonar.projects.create_project(project_key, name=repository_path)


    last_analysis = project['lastAnalysisDate'] if 'lastAnalysisDate' in project else None
    if last_analysis:
        local_tz = datetime.now().astimezone().tzinfo
        last_run_date = datetime.strptime(last_analysis, '%Y-%m-%dT%H:%M:%S%z').astimezone(local_tz)
        print(f"{INFO} Last analysis date: {last_run_date}")
    else:
        print(f"{INFO} No analysis has been done yet.")

    client = docker.from_env()

    print()
    print(f"{INFO} SonarQube 'sonar-scanner-cli' is performing analysis in the background...")
    try:
        env = {"SONAR_HOST_URL": f"http://localhost:{config.sonarqube_port}",
               "SONAR_SCANNER_OPTS": f"-Dsonar.projectKey={project_key} "
                                     f"-Dsonar.login={config.sonarqube_login} "
                                     f"-Dsonar.password={config.sonarqube_password} "
                                     f"-Dsonar.java.binaries=**/target"
               }
        client.containers.run("sonarsource/sonar-scanner-cli:4.8",
                              environment=env,
                              volumes={repository_path: {'bind': '/usr/src', 'mode': 'rw'}},
                              name="mura-sonarqube-scanner-instance",
                              remove=True,
                              network_mode='host',
                              detach=True)
    except Exception as e:
        print(f"{ERROR} Could not start SonarQube scanner. This is fatal.")
        raise e

    return project_key

def syntax_info(config: Configuration, project_key: str) -> ContributorWeight:
    header(f"{SYNTAX} Syntax + Semantics using SonarQube:")

    analysis_running = True
    client = docker.from_env()

    url = f'http://localhost:{config.sonarqube_port}'
    sonar = SonarQubeClient(sonarqube_url=url, username=config.sonarqube_login, password=config.sonarqube_password)

    while analysis_running:
        try:
            _ = client.containers.get("mura-sonarqube-scanner-instance")
            print(f"{INFO} Analysis is running. Waiting for it to finish...")
            sleep(2)
        except Exception as e:
            analysis_running = False
            print(f"{SUCCESS} SonarQube analysis finished.")
            print()

    issues = sonar.issues.search_issues(componentKeys=project_key)
    for issue in issues['issues']:
        print(issue['type'], issue['severity'], issue['message'])

    return defaultdict(lambda: 0.0)


def semantic_info(tracked_files: List[FileGroup],
                  ownership: Dict[Contributor, List[ContributionDistribution]],
                  semantics: List[List[Tuple[Path, SemanticWeightModel, 'LangElement']]]) \
        -> ContributorWeight:
    header(f"{SEMANTICS} Semantics:")

    contributor_weight: ContributorWeight = defaultdict(lambda: 0.0)

    for i in range(len(tracked_files)):
        group = tracked_files[i]
        group_sem = semantics[i]
        print(f"{FILE_GROUP} Group: {group.name}")
        print(f"Total files: {len(group.files)}")
        total_weight = 0.0
        for j in range(len(group.files)):
            if not group_sem or group_sem[j][1].is_empty:
                continue

            owner = get_owner(ownership, group.files[j])
            print(f"File: {group.files[j].name}: Owner: {owner.name if owner is not None else 'None'}")
            structure = group_sem[j][2]
            print(f"Contents: Classes: {len(list(structure.classes))} "
                  f"Functions: {len(list(structure.functions))} "
                  f"Properties: {len(list(structure.properties))} "
                  f"Fields: {len(list(structure.fields))} "
                  f"Comments: {len(list(structure.comments))} ")
            weight = structure.compute_weight(group_sem[j][1])
            print(f"{WEIGHT} Semantic file weight: {weight}")
            if owner is not None:
                contributor_weight[owner] += weight
            total_weight += weight

        print(f"{WEIGHT} Total weight: {total_weight}")
        print()

    return contributor_weight


def remote_info(commit_range: CommitRange, repo: Repo, config: Configuration, contributors: List[Contributor]) \
        -> ContributorWeight:
    header(f"{REMOTE_REPOSITORY} Remote repository management:")

    if config.ignore_remote_repo:
        print(f"{INFO} Skipping as 'config.ignore_remote_repo = True'")
        return {}

    start_date = commit_range.hist_commit.committed_datetime
    end_date = commit_range.head_commit.committed_datetime

    remote_url = repo.remote(name=config.default_remote_name).url
    project = parse_project(remote_url, config.gitlab_access_token, config.github_access_token)

    remote_weight_model = RemoteRepositoryWeightModel.load()

    print(f"Project: {project.name}")
    print(f"{ISSUES} Total issues: {len(project.issues)}")
    print(f"{PULL_REQUESTS} Total pull requests: {len(project.pull_requests)}")
    print(f"{CONTRIBUTOR} Total contributors: {len(project.members)}")

    contributor_weight: ContributorWeight = defaultdict(lambda: 0.0)

    for issue in project.issues:
        author_contributor = find_contributor(contributors, issue.author)
        header(f"{ISSUES} Issue: {issue.name} - by "
               f"{author_contributor.name if author_contributor is not None else 'None'}")
        print(f"Description: {issue.description}")
        print(f"State: {issue.state}")
        assignee = find_contributor(contributors, issue.assigned_to)
        closer = find_contributor(contributors, issue.closed_by)
        if issue.assigned_to:
            print(f"Assignee: {assignee.name if assignee is not None else 'None'}")
        if issue.closed_at is not None:
            print(f"Closed at: {issue.closed_at} by "
                  f"{closer.name if closer is not None else 'None'}")
        issue_weight = remote_weight_model.evaluate(issue, start_date, end_date)
        beneficiaries = []
        if assignee is not None:
            beneficiaries.append(assignee)
            contributor_weight[assignee] += issue_weight
        if closer is not None:
            beneficiaries.append(closer)
            contributor_weight[closer] += issue_weight
        if author_contributor is not None:
            beneficiaries.append(author_contributor)
            contributor_weight[author_contributor] += issue_weight

        print(f"{WEIGHT} Weight {issue_weight} - Beneficiaries: {', '.join(map(lambda x: x.name, beneficiaries))}")

    for pr in project.pull_requests:
        author_contributor = find_contributor(contributors, pr.author)
        print()
        header(f"{PULL_REQUESTS} Pull request: {pr.name} - by "
               f"{(author_contributor.name if author_contributor is not None else 'None')}")
        print(f"From: {pr.source_branch} to {pr.target_branch}")
        print(f"Description: {pr.description}")
        print(f"State: {pr.merge_status}")
        merger = find_contributor(contributors, pr.merged_by)
        if pr.merged_at is not None:
            print(f"Merged at: {pr.merged_at} by "
                  f"{merger.name if merger is not None else 'None'}")
        pr_weight = remote_weight_model.evaluate(pr, start_date, end_date)
        beneficiaries = []
        if merger is not None:
            beneficiaries.append(merger)
            contributor_weight[merger] += pr_weight
        author_contributor = find_contributor(contributors, pr.author)
        if author_contributor is not None:
            beneficiaries.append(author_contributor)
            contributor_weight[author_contributor] += pr_weight

        print(f"{WEIGHT} Weight {pr_weight} - Beneficiaries: {', '.join(map(lambda x: x.name, beneficiaries))}")

    return contributor_weight


def file_statistics_info(commit_range: CommitRange, contributors: List[Contributor]) \
        -> Dict[str, FlaggedFiles]:
    file_flags = get_flagged_files_by_contributor(commit_range, contributors)
    for contributor in contributors:
        print(f"{CONTRIBUTOR} {contributor})")
        for key, count in file_flags[contributor.name].counts.items():
            print(f" => {key} - {count}")
    return file_flags


def get_all_comments(element: LangElement) -> List[LangElement]:
    comments = []
    for child in element.children:
        if child.kind == 'comment':
            comments.append(child)
        else:
            comments.extend(get_all_comments(child))
    return comments


def constructs_info(tracked_files: List[FileGroup],
                    ownership: Dict[Contributor, List[ContributionDistribution]],
                    semantic_analysis_grouped_result: List[List[Tuple[Path, SemanticWeightModel, 'LangElement']]]):
    header(f"{SEMANTICS} Constructs:")
    user_constructs: Dict[Contributor, Dict[str, int]] = defaultdict(lambda: defaultdict(lambda: 0))
    for i in range(len(tracked_files)):
        file_group = tracked_files[i]
        semantic_group = semantic_analysis_grouped_result[i]
        for j in range(len(file_group.files)):
            file = file_group.files[j]
            owner = get_owner(ownership, file)
            element = semantic_group[j][2]
            for child in element.iterate():
                if child.kind == 'root':
                    continue
                if owner is None:
                    continue
                user_constructs[owner][child.kind] += 1

    for contrib, stats in user_constructs.items():
        print(f"{CONTRIBUTOR} {contrib.name}")
        print("  Owns:")
        for key, value in stats.items():
            print(f"   => {key} - {value}")


def lines_blanks_comments_info(repository: Repo,
                               ownership: Dict[Contributor, List[ContributionDistribution]],
                               semantic_analysis: List[List[Tuple[Path, SemanticWeightModel, 'LangElement']]],
                               tracked_files: List[FileGroup], contributors: List[Contributor]):
    header(f"{BLANKS_COMMENTS} Blanks and comments:")

    total_lines = 0
    tracked_file_count = 0
    largest_files = [(0, Path()) for _ in range(5)]
    smallest_files = [(sys.maxsize, Path()) for _ in range(5)]

    smallest_index = 0
    largest_index = 0

    for i in range(len(tracked_files)):
        file_group = tracked_files[i]
        for j in range(len(file_group.files)):
            file = file_group.files[j]
            element = semantic_analysis[i][j][2]
            # print(f"{INFO} File: {file.name}")
            lines = element.end
            # print(f"{INFO} Lines: {lines}")
            total_lines += lines
            if element.children:
                if lines < smallest_files[largest_index][0]:
                    smallest_files[largest_index] = (lines, file)
                    largest_index = smallest_files.index(max(smallest_files, key=lambda x: x[0]))
                if lines > largest_files[smallest_index][0]:
                    largest_files[smallest_index] = (lines, file)
                    smallest_index = largest_files.index(min(largest_files, key=lambda x: x[0]))
            tracked_file_count += 1

    print(f"{INFO} Total lines: {total_lines} across {tracked_file_count} files.")

    print(f"{INFO} Largest files:")
    for x in sorted(largest_files, key=lambda x: x[0], reverse=True):
        owner = get_owner(ownership, x[1])
        name = owner.name if owner is not None else "None"
        print(f" => {repo_p(str(x[1]), repository)} ({x[0]}) by {CONTRIBUTOR}: {name}")
    print(f"{INFO} Smallest files:")
    for x in sorted(smallest_files, key=lambda x: x[0]):
        owner = get_owner(ownership, x[1])
        name = owner.name if owner is not None else "None"
        print(f" => {repo_p(str(x[1]), repository)} ({x[0]}) by {CONTRIBUTOR}: {name}")

    print(f"{INFO} Blanks and comments in final version...")

    total_comments = 0
    file_count = 0

    for i in range(len(tracked_files)):
        file_group = tracked_files[i]
        for j in range(len(file_group.files)):
            file = file_group.files[j]
            element = semantic_analysis[i][j][2]
            # print(f"{INFO} File: {file.name}")
            comments = get_all_comments(element)
            # print(f"{INFO} Comments: {len(comments)}")
            file_comments = sum(map(lambda x: x.end - x.start, comments))
            total_comments += file_comments
            file_count += 1 if file_comments > 0 else 0
            # print(f"{INFO} Lines length: {file_comments}")

    print(f" => Total comments: {total_comments} lines across {file_count} files.")

    print(f"{PERCENT} Comment to code ratio: {(total_comments / total_lines) * 100:.2f}%")

    return None


def estimate_hours(dates: List[datetime], max_commit_diff: int = 120, first_commit_addition: int = 120) -> int:
    if len(dates) < 2:
        return 0

    # Oldest commit first, newest last
    sortedDates = sorted(dates)
    allButLast = sortedDates[:-1]

    hours = 0.0
    for index, date in enumerate(allButLast):
        nextDate = sortedDates[index + 1]
        diffInMinutes = (nextDate - date).total_seconds() / 60

        # Check if commits are counted to be in same coding session
        if diffInMinutes < max_commit_diff:
            hours += (diffInMinutes / 60)
        else:
            # The date difference is too big to be inside single coding session
            # The work of first commit of a session cannot be seen in git history,
            # so we make a blunt estimate of it
            hours += (first_commit_addition / 60)

    return round(hours)


def hour_estimates(contributors: List[Contributor], repository: Repo) -> Dict[Contributor, Tuple[int, int]]:
    header(f"{TIME} Hour estimates:")

    commits = [x for x in repository.iter_commits()]

    commits_by_author = defaultdict(lambda: [])

    for commit in commits:
        if commit.author.name is None:
            continue
        c = find_contributor(contributors, commit.author.name)
        commits_by_author[c].append(commit.committed_datetime)

    ret: Dict[Contributor, Tuple[int, int]] = {}

    for contributor in contributors:
        print(f"{CONTRIBUTOR} {contributor.name} has:")
        print(f" => {len(commits_by_author[contributor])} commits")
        hours = estimate_hours(commits_by_author[contributor])
        print(f" => {TIME} ~{hours} hours of work")
        ret[contributor] = (len(commits_by_author[contributor]), hours)

    print()

    return ret


def gaussian(configuration: Configuration, input_hours: float, hour_estimate: float):
    return configuration.base_hour_match_weight * \
        math.exp(-((input_hours - hour_estimate) ** 2) / (2 * hour_estimate * 2 ** 2))


def gaussian_weights(configuration: Configuration, hour_estimate: float,
                     hours: Dict[Contributor, Tuple[int, int]]) -> ContributorWeight:
    ret: Dict[Contributor, float] = defaultdict(lambda: 0.0)
    header(f"{WEIGHT} Gaussian weights:")
    for contributor, commits_hours in hours.items():
        print(f"{CONTRIBUTOR} {contributor.name}:")
        if commits_hours[1] != 0:
            weight = gaussian(configuration, hour_estimate, commits_hours[1])
            print(f" => {weight:.2f} {WEIGHT} Weight gained for: {commits_hours[1]} hours of work.")
            ret[contributor] += weight
        else:
            print(f" => {INFO} Estimated 0 hours.")

    return ret


def summary_info(contributors: List[Contributor],
                 syntactic_weights: ContributorWeight,
                 semantic_weights: ContributorWeight,
                 repo_management_weights: ContributorWeight,
                 global_rule_weight_multiplier: GlobalRuleWeightMultiplier,
                 hours: ContributorWeight) -> None:
    sums: Dict[Contributor, float] = defaultdict(lambda: 0.0)

    def print_section(section: ContributorWeight, add=True):
        if not section:
            print(f'{INFO} Nothing to show here...')
            return

        for contributor in contributors:
            if contributor in section:
                print(f" -> {contributor.name}: {section[contributor]}")
                if add:
                    sums[contributor] += section[contributor]

    separator()
    print(f"{WEIGHT} Total weight per contributor for {SYNTAX} Syntax:")
    print_section(syntactic_weights)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {SEMANTICS} Semantics:")
    print_section(semantic_weights)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {REMOTE_REPOSITORY} Remote repository management:")
    print_section(repo_management_weights)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {TIME} Estimated hours:")
    print_section(hours)

    separator()
    print(f"{WEIGHT}{WARN} Weight multiplier for unfulfilled {RULES} Rules:")
    print_section(global_rule_weight_multiplier, add=False)

    separator()
    print(f"{WEIGHT} Total weight per contributor:")

    for contributor in sums:
        sums[contributor] *= global_rule_weight_multiplier[contributor]

    position = 1
    for model in sorted(sums.items(), key=lambda x: x[1], reverse=True):
        assert isinstance(model, tuple)
        char = NUMBERS[position] if position <= len(NUMBERS) else f"{position}."
        print(f"{char} -> {model[0].name}: {model[1]:.2f}")
        position += 1


def display_results(repo: git.Repo,
                    commit_range: CommitRange,
                    syntax: AnalysisResult,
                    tracked_files: List[FileGroup],
                    semantics: List[List[Tuple[Path, SemanticWeightModel, 'LangElement']]],
                    config: Configuration,
                    project_key: str) -> None:
    contributors = display_contributor_info(commit_range, config)
    separator()
    commit_distribution, insertions_deletions = commit_info(commit_range, repo, contributors)
    separator()
    plot_commits([x for x in commit_range][1:], commit_range, contributors, repo)
    separator()
    file_flags = file_statistics_info(commit_range, contributors)
    separator()
    percentage, ownership = percentage_info(syntax, contributors, config)
    separator()
    display_dir_tree(config, percentage, repo)
    separator()
    global_rule_weight_multiplier = rule_info(config, repo, ownership, contributors)
    separator()
    syntax_weights = syntax_info(config, project_key)
    separator()
    semantic_weights = semantic_info(tracked_files, ownership, semantics)
    separator()
    repo_management_weights = remote_info(commit_range, repo, config, contributors)
    separator()
    hours = gaussian_weights(config, config.hour_estimate, hour_estimates(contributors, repo))
    separator()
    summary_info(contributors, syntax_weights, semantic_weights, repo_management_weights, global_rule_weight_multiplier,
                 hours)


if __name__ == '__main__':
    issue = Issue("", "", "", datetime.now(), None, "", "", "")
    assert isinstance(issue, Issue)
