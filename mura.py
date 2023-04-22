import argparse
import math
import os
import sys
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timezone, timedelta
from time import sleep
from typing import Tuple, List, Dict, Optional, Any

import docker  # type: ignore
from docker.models.containers import Container  # type: ignore
from git import Repo
from gitlab import GitlabListError
from matplotlib import pyplot as plt  # type: ignore
from matplotlib.dates import date2num, DateFormatter, drange  # type: ignore
from sonarqube import SonarQubeClient  # type: ignore
from sonarqube.utils.exceptions import AuthError  # type: ignore

import configuration
import file_analyzer
import semantic_analysis
from configuration import Configuration, start_sonar
from file_analyzer import FileWeight
from history_analyzer import AnalysisResult, calculate_percentage, CommitRange
from lib import FileGroup, Contributor, get_contributors, compute_file_ownership, find_contributor, \
    stats_for_contributor, get_flagged_files_by_contributor, ContributionDistribution, Percentage, \
    FlaggedFiles, repo_p, get_tracked_files
from remote_repository_weight_model import RemoteRepositoryWeightModel
from repository_hooks import parse_project, RemoteRepository, DummyRepository
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
            for owner, percentage_value in sub_ownership.items():
                ownership[owner] += percentage_value
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
                owners_str = ', '.join([f'{owner.name}: {value * 100:.0f}%' for owner, value in value.items() if owner.name != '?'])
                print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
            else:
                sub_ownerships = [calculate_ownership(v, ownership_cache) for v in value.values() if
                                  isinstance(v, dict)]
                if len(sub_ownerships) > 0 \
                        and all(sub_ownerships[0] == sub_ownership for sub_ownership in sub_ownerships):
                    print(f'{prefix}{connector}{name}')
                else:
                    owners_str = ', '.join([f'{owner.name}: {value * 100:.0f}%' for owner, value in
                                            calculate_ownership(value, ownership_cache).items() if owner.name != '?'])
                    print(f'{prefix}{connector}{name} {CONTRIBUTOR} [{owners_str}]')
                print_tree(value, level + 1, new_prefix, ownership_cache)


def plot_commits(commits: List[str], commit_range: CommitRange, contributors: List[Contributor],
                 force_x_axis_dense_labels=False, output_path: Optional[Path] = None) -> None:
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

    if output_path is not None:
        plt.savefig(output_path)
    else:
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
        print(f'Commit: {commit} - Msg: "{message}" by {CONTRIBUTOR} {contributor.name}')  # type: ignore

    print()
    header(f"{COMMIT} Commits per contributor:")

    for contrib, count in commit_distribution.items():
        print(f"{count} commits by: {CONTRIBUTOR} {contrib.name}")

    insertions_deletions = []

    for contrib in contributors:
        insertion, deletion = stats_for_contributor(contrib, commit_range)
        print(f"{CONTRIBUTOR} {contrib.name}: inserted '{insertion}' lines and deleted '{deletion}' lines.")
        insertions_deletions.append((contrib, insertion, deletion))

    return commit_distribution, insertions_deletions


def insertions_deletions_info(insertions_deletions: List[Tuple[Contributor, int, int]],
                              file_output: Optional[Path] = None) -> Any:
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

    if file_output is not None:
        plt.savefig(file_output)
    else:
        plt.show()


def percentage_info(analysis_res: AnalysisResult, contributors: List[Contributor], config: Configuration, repo: Repo) \
        -> Tuple[Percentage, Dict[Contributor, List[ContributionDistribution]]]:
    header(f'{PERCENTAGE} Percentage of tracked files:')

    percentage = calculate_percentage(contributors, analysis_res)

    for contributor_name, percent in percentage.global_contribution.items():
        print(f'\t{contributor_name}: {percent:.2%}')

    ownership = compute_file_ownership(percentage, config, repo)

    for contributor, contribution in ownership.items():
        print(f"Files owned by {CONTRIBUTOR} {contributor.name}")
        for contrib_distribution in contribution:
            print(f"\t{contrib_distribution}")
        print(f"Total: {len(contribution)} for {CONTRIBUTOR} {contributor}")

    return percentage, ownership


def display_dir_tree(percentage: Percentage, repo: Repo):
    header(f"{DIRECTORY_TREE} Dir Tree with ownership:")

    triples = []

    for key in percentage.file_per_contributor.keys():
        for name, percent in percentage.file_per_contributor[key]:
            triples.append((Path(os.path.relpath(key, repo.working_dir)), percent, name))

    tree = build_tree(triples)
    print_tree(tree)


def rule_info(config: Configuration, repo: Repo, ownership: Dict[Contributor, List[ContributionDistribution]],
              contributors: List[Contributor], remote_project: RemoteRepository) -> GlobalRuleWeightMultiplier:
    header(f"{RULES} Rules: ")

    ret: GlobalRuleWeightMultiplier = defaultdict(lambda: 1.0)

    for rule in config.parsed_rules.rules:
        print(rule)

    print()
    print(f"{WEIGHT} Weight Multipliers:")
    print(f"\tFile weight {config.file_rule_violation_multiplier}")
    print(f"\tIssue weight {config.issue_rule_violation_multiplier}")
    print(f"\tPull request weight {config.pr_rule_violation_multiplier}")

    print()
    header(f"{VIOLATED_RULES} Violated Rules: ")

    rule_result = config.parsed_rules.matches_files(repo, ownership)
    rule_result_remote = {}
    data_obtainable = True
    try:
        rule_result_remote = config.parsed_rules.matches_remote(contributors, remote_project)
    except GitlabListError as err:
        data_obtainable = False
        print(f"{ERROR} Could not access remote repository. Error: {err.response_code} Message: '{err.error_message}'")
        print(f"{INFO} No remote repository information will be presented.")

    if not rule_result and not rule_result_remote:
        print(f"{SUCCESS} No rules were violated.")
        return ret

    if not rule_result:
        print(f"{SUCCESS} No local rules were violated.")
    for c, file_rules in rule_result.items():
        rules_format = [('\t' + str(rule) + os.linesep) for rule in file_rules]
        print(f"{ERROR} {CONTRIBUTOR} Contributor: '{c.name}' did not fulfill the following requirements:")
        print("".join(rules_format), end='')
        for _ in file_rules:
            ret[c] *= config.file_rule_violation_multiplier

    if not rule_result_remote:
        if data_obtainable:
            print(f"{SUCCESS} No remote rules were violated.")
        else:
            print(f"{WARN} No remote repository data to analyze.")
    for c, remote_rules in rule_result_remote.items():
        rules_format = [('\t' + str(rule) + os.linesep) for rule in remote_rules]
        print(f"{ERROR} {CONTRIBUTOR} Contributor: '{c.name}' did not fulfill the following requirements:")
        print("".join(rules_format), end='')
        for r_rule in remote_rules:
            if r_rule.remote_object == 'issue':
                ret[c] *= config.issue_rule_violation_multiplier
            elif r_rule.remote_object == 'pr':
                ret[c] *= config.pr_rule_violation_multiplier

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


def local_syntax_analysis(config: Configuration, grouped_files: List[FileGroup]) -> Dict[Path, FileWeight]:
    ret: Dict[Path, FileWeight] = {}
    for group in grouped_files:
        for file in group.files:
            result = file_analyzer.compute_syntactic_weight(file, config)
            if not result:
                print(f"{INFO} Could not read text from {file} -> Unsupported format or Binary file!")
                continue
            ret[file] = result
    return ret


def start_sonar_analysis(config: Configuration, repository_path: str) \
        -> Tuple[Optional[str], Optional[Container]]:
    if not config.use_sonarqube:
        print(f"{INFO} Syntax analysis uses SonarQube and 'config.use_sonarqube = False'. Skipping syntax analysis.")
        return None, None

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
        except Exception:
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
    # try:
    #     commit_range.repo.git.execute(['git', 'checkout', '-b', 'sonar-analysis-head', commit_range.head])
    # except GitCommandError:
    #     try:
    #         commit_range.repo.git.execute(['git', 'branch', '-d', 'sonar-analysis-head'])
    #         commit_range.repo.git.execute(['git', 'checkout', '-b', 'sonar-analysis-head', commit_range.head])
    #     except GitCommandError:
    #         print("Could not create branch 'sonar-analysis-head' on current HEAD. "
    #               "This likely means that the branch already exists; and we are on it.")

    # print(f"{INFO} Switched to branch 'sonar-analysis-head' on current HEAD.")

    try:
        env = {"SONAR_HOST_URL": f"http://localhost:{config.sonarqube_port}",
               "SONAR_SCANNER_OPTS": f"-Dsonar.projectKey={project_key} "
                                     f"-Dsonar.login={config.sonarqube_login} "
                                     f"-Dsonar.password={config.sonarqube_password} "
                                     f"-Dsonar.java.binaries=**/target"
               #                     f"-Dsonar.branch.name=sonar-analysis-head" TODO not available in standard edition
               }
        container = client.containers.run("sonarsource/sonar-scanner-cli:4.8",
                                          environment=env,
                                          volumes={repository_path: {'bind': '/usr/src', 'mode': 'rw'}},
                                          name="mura-sonarqube-scanner-instance",
                                          remove=config.remove_analysis_container_on_analysis_end,
                                          network_mode='host',
                                          detach=True)
    except Exception as ex:
        print(f"{ERROR} Could not start SonarQube scanner. This is fatal.")
        raise ex

    return project_key, container


def local_syntax_info(config: Configuration, ownership: Dict[Contributor, List[ContributionDistribution]],
                      local_syntax: Dict[Path, FileWeight], repo: Repo, file_maturity_score: Dict[Path, float],
                      n_extreme_files: int = 5) -> ContributorWeight:
    header("Raw file weights:")

    assert n_extreme_files >= 0, "n_extreme_files must be non-negative."

    highest_weighted_files = [(-math.inf, Path()) for _ in range(n_extreme_files)]
    lowest_weighted_files = [(math.inf, Path()) for _ in range(n_extreme_files)]

    lowest_index = 0
    highest_index = 0

    print(f"{INFO} Base file weight: {config.single_file_weight}")

    ret: ContributorWeight = defaultdict(lambda: 0.0)
    per_contributor = defaultdict(list)

    for file, file_weight_inst in local_syntax.items():
        if n_extreme_files > 0:
            if file_weight_inst.file_weight < lowest_weighted_files[highest_index][0]:
                lowest_weighted_files[highest_index] = (file_weight_inst.file_weight, file)
                highest_index = lowest_weighted_files.index(max(lowest_weighted_files, key=lambda k: k[0]))
            if file_weight_inst.file_weight > highest_weighted_files[lowest_index][0]:
                highest_weighted_files[lowest_index] = (file_weight_inst.file_weight, file)
                lowest_index = highest_weighted_files.index(min(highest_weighted_files, key=lambda k: k[0]))

        contributor = get_owner(ownership, file)
        mult_note = ""
        if file in file_maturity_score:
            file_weight_inst.file_weight *= file_maturity_score[file]
            mult_note = f" adjusted *({file_maturity_score[file]})"
        print(f" - {file} -> {WEIGHT} Weight: {file_weight_inst.syntactic_weight}" + mult_note)
        if not contributor:
            continue
        per_contributor[contributor].append(file_weight_inst.syntactic_weight)
        ret[contributor] += file_weight_inst.syntactic_weight

    print()
    print("Averages:")

    for contrib, weights in per_contributor.items():
        print(f"{CONTRIBUTOR} {contrib.name} - {WEIGHT} Average weight: "
              f"{sum(weights) / len(weights)}")

    print()
    if n_extreme_files > 0:
        print(f"{INFO} Highest weighted files:")
        for x in sorted(highest_weighted_files, key=lambda k: k[0], reverse=True):
            owner = get_owner(ownership, x[1])
            name = owner.name if owner is not None else "None"
            print(f" => {repo_p(str(x[1]), repo)} ({x[0]}) by {CONTRIBUTOR}: {name}")

        print(f"{INFO} Lowest weighted files:")
        for x in sorted(lowest_weighted_files, key=lambda k: k[0]):
            owner = get_owner(ownership, x[1])
            name = owner.name if owner is not None else "None"
            print(f" => {repo_p(str(x[1]), repo)} ({x[0]}) by {CONTRIBUTOR}: {name}")

    return ret


def sonar_info(config: Configuration, contributors: List[Contributor], repo: Repo,
               file_ownership: Dict[Contributor, List[ContributionDistribution]],
               project_key: Optional[str]) -> ContributorWeight:
    header(f"{SYNTAX} Syntax + Semantics using SonarQube:")

    if not config.use_sonarqube:
        print(f"{INFO} Syntax analysis uses SonarQube and 'config.use_sonarqube = False'. Skipping syntax analysis.")
        return {}

    analysis_running = True
    client = docker.from_env()

    url = f'http://localhost:{config.sonarqube_port}'
    sonar = SonarQubeClient(sonarqube_url=url, username=config.sonarqube_login, password=config.sonarqube_password)

    while analysis_running:
        try:
            _ = client.containers.get("mura-sonarqube-scanner-instance")
            print(f"{INFO} Analysis is running. Waiting for it to finish...")
            sleep(2)
        except Exception:
            analysis_running = False
            print(f"{SUCCESS} SonarQube analysis finished.")
            sleep(2)
            print()

    class IssueDef:
        def __init__(self, severity: str, message: str, file: str, line: int):
            self.severity = severity
            self.message = message
            self.file = file
            self.line = line

    class HotspotDef:
        def __init__(self, severity: str, message: str, file: str, line: int):
            self.severity = severity
            self.message = message
            self.file = file
            self.line = line

    sonar_projects = sonar.projects.search_projects()
    project = None
    for proj in sonar_projects['components']:
        if proj['key'] == project_key:
            project = proj
            break
    if project is None:
        print(f"{ERROR} Project {project_key} not found in SonarQube. Skipping analysis.")
        print(f"{ERROR} Something went very wrong. Did the analysis container fail?")
        return {}

    counter = 0
    while 'lastAnalysisDate' not in project and counter < 10:
        sonar_projects = sonar.projects.search_projects()
        for proj in sonar_projects['components']:
            if proj['key'] == project_key:
                project = proj
                break
        counter += 1
        if 'lastAnalysisDate' not in project:
            print(f"{INFO} Project {project_key} has no analysis. Waiting for Sonar to update its database...")
        else:
            date = datetime.strptime(project['lastAnalysisDate'], '%Y-%m-%dT%H:%M:%S%z')
            if date < (datetime.now() - timedelta(minutes=5)).astimezone():
                if counter == 10:
                    print(f"{ERROR} Project {project_key} has an old analysis. Database not updated in time.")
                    print(f"{ERROR} Something went very wrong. Did the analysis container fail?")
                    return {}
                print(f"{INFO} Project {project_key} has an old analysis. Waiting for Sonar to update its database...")
            else:
                print(f"{SUCCESS} SonarQube database updated. Last analysis: {date}")
                counter = 0
                break

    if counter == 10:
        print(f"{ERROR} Project {project_key} not found in SonarQube. Skipping analysis.")
        print(f"{ERROR} Something went very wrong. Did the analysis container fail?")
        return {}

    issues_per_contributor: Dict[Contributor, List[IssueDef]] = defaultdict(list)

    issue_page = 1

    all_issues = []
    response = sonar.issues.search_issues(componentKeys=project_key, p=issue_page)
    all_issues.extend(response['issues'])
    while response['paging']['total'] > issue_page * response['paging']['pageSize']:
        issue_page += 1
        response = sonar.issues.search_issues(componentKeys=project_key, p=issue_page)
        all_issues.extend(response['issues'])

    if len(all_issues) > 0:
        header(f"{HOTSPOT} Reported Issues:")
    else:
        print(f"{INFO} No issues reported by SonarQube. This is likely suspicious. Did the analysis container fail?")
        print(f"{INFO} You can set 'config.remove_analysis_container_on_analysis_end = False' to debug the container.")
        print(f"{INFO} Otherwise the project is perfect 'Great success! {SUCCESS}'.")

    for issue in all_issues:
        contributor = find_contributor(contributors, issue['author'])
        line = issue['line'] if 'line' in issue else -1
        issue_def = IssueDef(issue['severity'], issue['message'], issue['component'].split(':')[1], line)
        file_path = Path(repo_p(issue_def.file, repo))
        print(f"{WARN} Severity: {issue_def.severity} --> '{issue_def.message}")
        print(f" -> In file: {repo_p(str(file_path), repo)}:{issue_def.line}")
        if not contributor:
            contributor = get_owner(file_ownership, file_path)
        if not contributor:
            print(f"{WARN} Could not determine who owns this issue. Distributing to all contributors.")
            for c in contributors:
                issues_per_contributor[c].append(issue_def)
        else:
            issues_per_contributor[contributor].append(issue_def)

    print()
    ret: ContributorWeight = defaultdict(lambda: 0.0)

    for contrib, issues in issues_per_contributor.items():
        print(f"{CONTRIBUTOR} {contrib.name} has: {len(issues)} issues.")
        for issue in issues:
            if issue.severity == 'BLOCKER':
                ret[contrib] += config.sonar_blocker_severity_weight
            elif issue.severity == 'CRITICAL':
                ret[contrib] += config.sonar_critical_severity_weight
            elif issue.severity == 'MAJOR':
                ret[contrib] += config.sonar_major_severity_weight
            elif issue.severity == 'MINOR':
                ret[contrib] += config.sonar_minor_severity_weight

    print()

    hotspot_page = 1

    all_hotspots = []
    response = sonar.hotspots.search_hotspots(projectKey=project_key, p=hotspot_page)
    all_hotspots.extend(response['hotspots'])
    while response['paging']['total'] > hotspot_page * response['paging']['pageSize']:
        hotspot_page += 1
        response = sonar.hotspots.search_hotspots(projectKey=project_key, p=hotspot_page)
        all_hotspots.extend(response['hotspots'])

    if len(all_hotspots) > 0:
        header(f"{HOTSPOT} Security concerns:")

    for sec in all_hotspots:
        contributor = find_contributor(contributors, sec['author'])
        hotspot_def = HotspotDef(sec['vulnerabilityProbability'], sec['message'],
                                 sec['component'].split(':')[1], sec['line'])
        file_path = Path(repo_p(hotspot_def.file, repo))
        print(f"{WARN} Severity: {hotspot_def.severity} --> '{hotspot_def.message}")
        print(f" -> In file: {repo_p(str(file_path), repo)}:{hotspot_def.line}")
        if not contributor:
            print(f"{WARN} Could not determine who owns this hot-spot.")

    print()

    print(f"{INFO} All of the presented information were extracted from http://localhost:{config.sonarqube_port}.")

    return ret


def semantic_info(tracked_files: List[FileGroup],
                  ownership: Dict[Contributor, List[ContributionDistribution]],
                  semantics: List[List[Tuple[Path, SemanticWeightModel, 'LangElement']]],
                  file_maturity_score: Dict[Path, float]) \
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
            mult_note = ""
            if group.files[j] in file_maturity_score:
                weight *= file_maturity_score[group.files[j]]
                mult_note = f" adjusted *({file_maturity_score[group.files[j]]})"
            print(f"{WEIGHT} Semantic file weight: {weight}" + mult_note)

            if owner is not None:
                contributor_weight[owner] += weight
            total_weight += weight

        print(f"{WEIGHT} Total weight: {total_weight}")
        print()

    return contributor_weight


def remote_info(commit_range: CommitRange, repo: Repo, config: Configuration, contributors: List[Contributor]) \
        -> Tuple[RemoteRepository, ContributorWeight]:
    header(f"{REMOTE_REPOSITORY} Remote repository management:")

    if config.ignore_remote_repo:
        print(f"{INFO} Skipping as 'config.ignore_remote_repo = True'")
        return DummyRepository(), {}

    start_date = commit_range.hist_commit.committed_datetime
    end_date = commit_range.head_commit.committed_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)

    remote_url = repo.remote(name=config.default_remote_name).url
    project = parse_project(remote_url, config.gitlab_access_token, config.github_access_token)

    remote_weight_model = RemoteRepositoryWeightModel.load()

    try:
        restricted_issues = [x for x in project.issues if start_date < x.created_at < end_date or
                             x.closed_at is not None and start_date < x.closed_at < end_date]
        restricted_prs = [x for x in project.pull_requests if start_date < x.created_at < end_date or
                          x.merged_at is not None and start_date < x.merged_at < end_date]
    except GitlabListError as ex:
        print(f"{ERROR} Could not access remote repository. Error: {ex.response_code} Message: '{ex.error_message}'")
        print(f"{INFO} No remote repository information will be presented.")
        return project, {}

    print(f"Project: {project.name}")
    print(f"{ISSUES} Total issues: {len(restricted_issues)}")
    print(f"{PULL_REQUESTS} Total pull requests: {len(restricted_prs)}")
    print(f"{CONTRIBUTOR} Total contributors: {len(project.members)}")
    remote_url_print = remote_url if not config.anonymous_mode else "'<anonymous_remote_url>'"
    print(f"{INFO} All of the presented information were extracted from {remote_url_print}.")
    print(f"{INFO} Checking for issues and pull requests between {start_date} and {end_date}.")
    print()

    contributor_weight: ContributorWeight = defaultdict(lambda: 0.0)

    for issue in restricted_issues:
        author_contributor = find_contributor(contributors, issue.author)
        header(f"{ISSUES} Issue: {issue.name} - by "
               f"{author_contributor.name if author_contributor is not None else 'None'}")
        print(f"Link: {issue.url}")
        print(f"Description: {issue.description}")
        # print(f"State: {issue.state}") # TODO this is not very intuitive
        assignee = find_contributor(contributors, issue.assigned_to)
        closer = find_contributor(contributors, issue.closed_by)
        if issue.assigned_to:
            print(f"Assignee: {assignee.name if assignee is not None else 'None'}")
        if issue.closed_at is not None:
            print(f"Closed at: {issue.closed_at} by "
                  f"{closer.name if closer is not None else 'None'}")
        issue_weight = remote_weight_model.evaluate(issue, start_date, end_date)
        beneficiaries = set()
        if assignee is not None:
            beneficiaries.add(assignee)
            contributor_weight[assignee] += issue_weight
        if closer is not None:
            beneficiaries.add(closer)
            contributor_weight[closer] += issue_weight
        if author_contributor is not None:
            beneficiaries.add(author_contributor)
            contributor_weight[author_contributor] += issue_weight

        print(f"{WEIGHT} Weight {issue_weight} - Beneficiaries: {', '.join(map(lambda x: x.name, beneficiaries))}")
        print()

    for pr in restricted_prs:
        author_contributor = find_contributor(contributors, pr.author)
        print()
        header(f"{PULL_REQUESTS} Pull request: {pr.name} - by "
               f"{(author_contributor.name if author_contributor is not None else 'None')}")
        print(f"From: {pr.source_branch} to {pr.target_branch}")
        print(f"Link: {pr.url}")
        print(f"Description: {pr.description}")
        # print(f"State: {pr.merge_status}") # TODO this reports can_be_merged, while already merged
        merger = find_contributor(contributors, pr.merged_by)
        if pr.merged_at is not None:
            print(f"Merged at: {pr.merged_at} by "
                  f"{merger.name if merger is not None else 'None'}")
        pr_weight = remote_weight_model.evaluate(pr, start_date, end_date)
        beneficiaries = set()
        if merger is not None:
            beneficiaries.add(merger)
            contributor_weight[merger] += pr_weight
        author_contributor = find_contributor(contributors, pr.author)
        if author_contributor is not None:
            beneficiaries.add(author_contributor)
            contributor_weight[author_contributor] += pr_weight

        print(f"{WEIGHT} Weight {pr_weight} - Beneficiaries: {', '.join(map(lambda x: x.name, beneficiaries))}")
        print()

    return project, contributor_weight


def file_statistics_info(commit_range: CommitRange, contributors: List[Contributor]) \
        -> Dict[str, FlaggedFiles]:
    file_flags = get_flagged_files_by_contributor(commit_range, contributors)
    for contributor in contributors:
        if contributor.name == '?':
            continue
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
                               semantic_analysis_res: List[List[Tuple[Path, SemanticWeightModel, 'LangElement']]],
                               tracked_files: List[FileGroup],
                               n_extreme_files: int = 5):
    header(f"{BLANKS_COMMENTS} Blanks and comments:")

    assert n_extreme_files >= 0, 'n_extreme_files must be a non-negative number!'

    total_lines = 0
    tracked_file_count = 0
    largest_files = [(0, Path()) for _ in range(n_extreme_files)]
    smallest_files = [(sys.maxsize, Path()) for _ in range(n_extreme_files)]

    smallest_index = 0
    largest_index = 0

    for i in range(len(tracked_files)):
        file_group = tracked_files[i]
        for j in range(len(file_group.files)):
            file = file_group.files[j]
            element = semantic_analysis_res[i][j][2]
            # print(f"{INFO} File: {file.name}")
            lines = element.end
            # print(f"{INFO} Lines: {lines}")
            total_lines += lines
            if element.children and n_extreme_files > 0:
                if lines < smallest_files[largest_index][0]:
                    smallest_files[largest_index] = (lines, file)
                    largest_index = smallest_files.index(max(smallest_files, key=lambda k: k[0]))
                if lines > largest_files[smallest_index][0]:
                    largest_files[smallest_index] = (lines, file)
                    smallest_index = largest_files.index(min(largest_files, key=lambda k: k[0]))
            tracked_file_count += 1

    print(f"{INFO} Total lines: {total_lines} across {tracked_file_count} files.")

    if n_extreme_files > 0:
        print(f"{INFO} Largest files:")
        for x in sorted(largest_files, key=lambda k: k[0], reverse=True):
            owner = get_owner(ownership, x[1])
            name = owner.name if owner is not None else "None"
            print(f" => {repo_p(str(x[1]), repository)} ({x[0]}) by {CONTRIBUTOR}: {name}")
        print(f"{INFO} Smallest files:")
        for x in sorted(smallest_files, key=lambda k: k[0]):
            owner = get_owner(ownership, x[1])
            name = owner.name if owner is not None else "None"
            print(f" => {repo_p(str(x[1]), repository)} ({x[0]}) by {CONTRIBUTOR}: {name}")

    print(f"{INFO} Blanks and comments in final version...")

    total_comments = 0
    file_count = 0

    for i in range(len(tracked_files)):
        file_group = tracked_files[i]
        for j in range(len(file_group.files)):
            element = semantic_analysis_res[i][j][2]
            # print(f"{INFO} File: {file.name}")
            comments = get_all_comments(element)
            # print(f"{INFO} Comments: {len(comments)}")
            file_comments = sum(map(lambda k: k.end - k.start, comments))
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
    sorted_dates = sorted(dates)
    all_but_last = sorted_dates[:-1]

    hours = 0.0
    for index, date in enumerate(all_but_last):
        next_date = sorted_dates[index + 1]
        diff_in_minutes = (next_date - date).total_seconds() / 60

        # Check if commits are counted to be in same coding session
        if diff_in_minutes < max_commit_diff:
            hours += (diff_in_minutes / 60)
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


def gaussian(config: Configuration, input_hours: float, hour_estimate: float):
    return config.base_hour_match_weight * \
        math.exp(-((input_hours - hour_estimate) ** 2) / (2 * hour_estimate * 2 ** 2))


def gaussian_weights(config: Configuration, hour_estimate: float,
                     hours: Dict[Contributor, Tuple[int, int]]) -> ContributorWeight:
    ret: Dict[Contributor, float] = defaultdict(lambda: 0.0)
    header(f"{WEIGHT} Gaussian weights:")
    for contributor, commits_hours in hours.items():
        print(f"{CONTRIBUTOR} {contributor.name}:")
        if commits_hours[1] != 0:
            weight = gaussian(config, hour_estimate, commits_hours[1])
            print(f" => {weight:.2f} {WEIGHT} Weight gained for: {commits_hours[1]} hours of work.")
            ret[contributor] += weight
        else:
            print(f" => {INFO} Estimated 0 hours.")

    return ret


def summary_info(contributors: List[Contributor],
                 sonar_weights: ContributorWeight,
                 semantic_weights: ContributorWeight,
                 local_syntax: ContributorWeight,
                 repo_management_weights: ContributorWeight,
                 global_rule_weight_multiplier: GlobalRuleWeightMultiplier,
                 hours: ContributorWeight,
                 file_history_multipliers: Dict[Path, float]) -> None:
    sums: Dict[Contributor, float] = defaultdict(lambda: 0.0)

    def print_section(section: ContributorWeight, add=True):
        if not section:
            print(f'{INFO} Nothing to show here...')
            return

        for contrib in contributors:
            if contrib in section:
                print(f" -> {contrib.name}: {section[contrib]:.2f}")
                if add:
                    sums[contrib] += section[contrib]

    separator()
    print(f"{WEIGHT} Total weight per contributor for {CUBE} SonarQube analysis:")
    print(f"{INFO} These weights are negative, that is intentional, "
          f"as the analysis goes though the issues and security concerns.")
    print_section(sonar_weights)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {SEMANTICS} Semantics:")
    print_section(semantic_weights)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {SYNTAX} Syntax:")
    print_section(local_syntax)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {REMOTE_REPOSITORY} Remote repository management:")
    print_section(repo_management_weights)

    separator()
    print(f"{WEIGHT} Total weight per contributor for {TIME} Estimated hours:")
    print_section(hours)

    separator()
    print(f"{WEIGHT}{WARN} Weight multiplier for unfulfilled {RULES} Rules:")
    print_section(global_rule_weight_multiplier, add=False)

    # separator()
    # print(f"{WEIGHT}{WARN} Total multiplier for file history:")
    # print(f"{INFO} This multiplier is applied to: {SEMANTICS} Semantics and {SYNTAX} Syntax, "
    #       f"the above results are WITH the multiplier.")
    # for path, multiplier in [x for x in file_history_multipliers.items() if x[1] != 1.0]:
    #     print(f" -> {path}: {multiplier}")

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


# https://stackoverflow.com/a/8384788
def path_leaf(path):
    import ntpath
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def display_results(arguments: argparse.Namespace) -> None:
    import fs_access as file_system

    repository_path = arguments.repo

    repo = Repo(repository_path)
    commit_range = CommitRange(repo, arguments.head, arguments.root, verbose=True)

    config = configuration.validate()

    config.ignore_remote_repo = arguments.ignore_remote_repo
    config.use_sonarqube = arguments.use_sonarqube
    config.sonarqube_persistent = arguments.sq_persistent
    config.remove_analysis_container_on_analysis_end = arguments.sq_remove_analysis_container_on_analysis_end
    config.sonarqube_login = arguments.sq_login
    config.sonarqube_password = arguments.sq_password
    config.sonarqube_port = arguments.sq_port

    config.check_whitespace_changes = arguments.check_whitespace_changes
    config.ignored_extensions = arguments.ignored_extensions

    config.post_validate()

    config.contributor_map = arguments.contributor_map

    repository = file_system.validate_repository(repository_path, config)

    config.anonymous_mode = arguments.anonymous_mode

    contributors = display_contributor_info(commit_range, config)

    project_key, container = start_sonar_analysis(config, repository_path)

    tracked_files = get_tracked_files(repository, verbose=True)
    history_analysis_result = commit_range.analyze(verbose=True)
    syntactic_analysis_result = local_syntax_analysis(config, tracked_files)
    file_history_multiplier = file_analyzer.assign_scores(tracked_files, history_analysis_result, config)

    semantic_analysis_grouped_result = semantic_analysis.compute_semantic_weight_result(config, tracked_files,
                                                                                        verbose=True)
    separator()
    commit_distribution, insertions_deletions = commit_info(commit_range, repo, contributors)
    insertions_deletions_info(insertions_deletions, Path(repository_path) / "ins_del.png")
    separator()
    plot_commits([x for x in commit_range][1:], commit_range, contributors,
                 output_path=Path(repository_path) / "commits.png")
    separator()
    _ = file_statistics_info(commit_range, contributors)
    separator()
    percentage, ownership = percentage_info(history_analysis_result, contributors, config, repo)
    separator()
    display_dir_tree(percentage, repo)
    separator()

    lines_blanks_comments_info(repository, ownership, semantic_analysis_grouped_result, tracked_files,
                               n_extreme_files=5)
    separator()
    commit_range.unmerged_commits_info(repository, config, contributors)
    separator()
    sonar_weights = sonar_info(config, contributors, repo, ownership, project_key)
    separator()
    local_syntax_weights = local_syntax_info(config, ownership, syntactic_analysis_result, repo,
                                             file_history_multiplier)
    separator()
    semantic_weights = semantic_info(tracked_files, ownership, semantic_analysis_grouped_result,
                                     file_history_multiplier)
    separator()
    constructs_info(tracked_files, ownership, semantic_analysis_grouped_result)
    separator()
    hours = hour_estimates(contributors, repository)

    hour_weights = gaussian_weights(config, arguments.hour_estimate_per_contributor, hours)
    separator()
    project, repo_management_weights = remote_info(commit_range, repo, config, contributors)
    separator()
    global_rule_weight_multiplier = rule_info(config, repo, ownership, contributors, project)
    separator()
    summary_info(contributors, sonar_weights, semantic_weights, local_syntax_weights, repo_management_weights,
                 global_rule_weight_multiplier, hour_weights, file_history_multiplier)


def contributor_pairs(contributor_map):
    key, value = contributor_map.split(':')
    return key, value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MURA - MOTH | Repository Analyzer')
    parser.add_argument('-r', '--repo', type=str, required=True,
                        help='A string representing a path to a repository')
    parser.add_argument('--head', type=str, default='HEAD', metavar="HEXSHA",
                        help='The head commit - representing the final commit that will be analyzed')
    parser.add_argument('--root', type=str, default='ROOT', metavar="HEXSHA",
                        help='The root commit - representing the starting point in history')
    parser.add_argument('-f', '--file', type=str, default='', metavar="PATH",
                        help='Where to store the output of this script, default prints to stdout')
    parser.add_argument('--contributor-map', type=contributor_pairs, nargs='*', action='append', default=[],
                        metavar='"C":"C"',
                        help='A variable number of "contributor_name":"contributor_name" type inputs')
    parser.add_argument('--hour_estimate_per_contributor', type=int, default=24, metavar='N',
                        help='The expected amount of hours students are expected to spend on the project '
                             '(for the given commit range), used for hour weight estimation.')
    parser.add_argument('--anonymous-mode', type=bool, default=False, metavar="BOOL",
                        help='Anonymous mode, All contributor names will be replaced with "Contributor #n"')
    parser.add_argument('--use-sonarqube', type=bool, default=True, metavar="BOOL",
                        help='Use SonarQube')
    parser.add_argument('--sq-persistent', type=bool, default=True, metavar="BOOL",
                        help='SonarQube persistent')
    parser.add_argument('--sq-remove-analysis-container-on-analysis-end', type=bool, default=True, metavar="BOOL",
                        help='Remove analysis container on analysis end')
    parser.add_argument('--sq-login', type=str, default='admin', metavar="STR",
                        help='SonarQube login')
    parser.add_argument('--sq-password', type=str, default='admin', metavar="STR",
                        help='SonarQube password')
    parser.add_argument('--sq-port', type=int, default=8080, metavar="PORT",
                        help='SonarQube port')
    parser.add_argument('--check-whitespace-changes', type=bool, default=True, metavar="BOOL",
                        help='Check for whitespace changes in the file')
    parser.add_argument('--ignored-extensions', type=str, nargs='+', default=[], metavar="EXT",
                        help='Extensions to ignore during analysis')
    parser.add_argument('--ignore-remote-repo', type=bool, default=False, metavar="BOOL",
                        help='Ignore remote repository, in case of no internet connection or other reasons')

    args = parser.parse_args()

    if args.file != '':
        try:
            with open(args.file, 'w', encoding='UTF-8') as f:
                with redirect_stdout(f):
                    try:
                        display_results(args)
                    except Exception as inner:
                        header("")
                        print(f"{ERROR} MURA failed to run, please check the following error:")
                        print(inner)
        except Exception as e:
            print(e)
            print(f"Failed to write to file: '{args.file}'")
            sys.exit(1)
