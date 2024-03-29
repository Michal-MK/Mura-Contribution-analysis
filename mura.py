'''
Driver script for the Jupiter notebook
Aggregates the results of the analysis and generates the plots
'''
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
import fs_access
import semantic_analysis
from analyzers.plots.commit_ditribution import plot_commits
from analyzers.dir_tree import build_tree, print_tree
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


def get_owner(ownership: Dict[Contributor, List[ContributionDistribution]], file: Path) -> Optional[Contributor]:
    '''
    Reverse lookup for the owner of a file
    '''

    for k, v in ownership.items():
        if file in map(lambda x: x.file, v):
            return k
    return None


'''
Helper functions for output formatting
'''


def separator(section_end: bool = False) -> None:
    print()
    print("============================================")
    if section_end:
        print("  ", end="")
    print()


def header(text: str, machine_id: str = "") -> None:
    if machine_id:
        print(f" +{machine_id}")
    print(text)


def display_contributor_info(commit_range: CommitRange, config: Configuration) -> List[Contributor]:
    '''
    Driver function for contributor overview
    '''

    header(f"{CONTRIBUTOR} Contributors:", machine_id="contributors")

    contributors = get_contributors(config, commit_range=commit_range)

    for contrib in contributors:
        if contrib.name == '?' and contrib.email == '?':
            continue
        print(contrib)

    print()
    return contributors


def display_commit_info(commit_range: CommitRange, repo: Repo, contributors: List[Contributor], config: Configuration) \
        -> Tuple[Dict[Contributor, int], List[Tuple[Contributor, int, int]]]:
    '''
    Driver function for commit overview
    '''

    header(f"{COMMIT} Total commits: {len(commit_range.compute_path())}", machine_id="commits")

    commit_distribution: Dict[Contributor, int] = defaultdict(lambda: 0)

    for commit in commit_range:
        raw_commit = commit_range.commit(commit)
        author = raw_commit.author.name
        if author is None:
            continue
        contributor = find_contributor(contributors, author)
        if contributor is None:
            print(f'{INFO} Autor {author} not found in contributors. Skipping commit.')
            continue
        commit_distribution[contributor] += 1
        split = repo.commit(commit).message.splitlines()
        message = split[0] if len(split) > 0 else ''
        print(f'Commit: {commit} - Msg: "{message}" - Date: `{raw_commit.committed_datetime}` by {CONTRIBUTOR} {contributor.name}')  # type: ignore

    if config.prescan_mode:
        return commit_distribution, []

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
                              config: Configuration,
                              output_path: Optional[Path] = None) -> Any:
    '''
    Plotting function for insertions and deletions
    '''

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

    if output_path is not None:
        plt.savefig(output_path)
    else:
        if (not config.no_graphs):
            plt.show()


def display_percentage_info(analysis_res: AnalysisResult, contributors: List[Contributor], config: Configuration,
                            repo: Repo) \
        -> Tuple[Percentage, Dict[Contributor, List[ContributionDistribution]]]:
    '''
    Driver code for calculating and displaying percentage information.
    '''

    header(f'{PERCENTAGE} Percentage of tracked files:', machine_id="percentage")

    percentage = calculate_percentage(contributors, analysis_res)

    for contributor_name, percent in percentage.global_contribution.items():
        if contributor_name == '?':
            continue
        print(f'\t{contributor_name}: {percent:.2%}')

    ownership = compute_file_ownership(percentage, config, repo)

    for contributor, contribution in ownership.items():
        if contributor.name == '?':
            continue
        print(f"Files owned by {CONTRIBUTOR} {contributor.name}")
        for contrib_distribution in contribution:
            print(f"\t{contrib_distribution}")
        print(f"Total: {len(contribution)} for {CONTRIBUTOR} {contributor}")

    return percentage, ownership


def display_dir_tree(percentage: Percentage, repo: Repo):
    '''
    Driver code for ownership tree rendering
    '''

    header(f"{DIRECTORY_TREE} Dir Tree with ownership:", machine_id="dir_tree")

    triples = []

    for key in percentage.file_per_contributor.keys():
        for name, percent in percentage.file_per_contributor[key]:
            triples.append((Path(os.path.relpath(key, repo.working_dir)), percent, name))

    tree = build_tree(triples)
    print_tree(tree)


def display_rule_info(config: Configuration, repo: Repo, ownership: Dict[Contributor, List[ContributionDistribution]],
                      contributors: List[Contributor], remote_project: RemoteRepository) -> Dict[Contributor, float]:
    '''
    Driver code for Rule based analysis
    '''
    header(f"{RULES} Rules: ", machine_id="rules")

    ret: Dict[Contributor, float] = defaultdict(lambda: 1.0)

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
    '''
    Starts the SonarQube server instance and the analysis container with the given repository.
    In case the container fails to start, None is returned for both project-key and container.
    '''

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

    # TODO SonarQube Community Edition does not support branch analysis...
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
               #                     f"-Dsonar.branch.name=sonar-analysis-head" TODO not available in Community Edition
               }
        container = client.containers.run("sonarsource/sonar-scanner-cli:4.8",
                                          environment=env,
                                          volumes={repository_path: {'bind': '/usr/src', 'mode': 'rw'}},
                                          name="mura-sonarqube-scanner-instance",
                                          remove=not config.sonarqube_keep_analysis_container,
                                          network_mode='host',
                                          detach=True)
    except Exception as ex:
        print(f"{ERROR} Could not start SonarQube scanner. This is fatal.")
        raise ex

    return project_key, container


def display_local_syntax_info(config: Configuration, ownership: Dict[Contributor, List[ContributionDistribution]],
                              local_syntax: Dict[Path, FileWeight], repo: Repo, file_maturity_score: Dict[Path, float],
                              n_extreme_files: int = 5) -> ContributorWeight:
    '''
    Driver function for local syntax analysis.
    '''

    header(f"{SYNTAX} Local Syntax Analysis", machine_id="local_syntax")

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
        print(f" - {repo_p(str(file), repo)} -> {WEIGHT} Weight: {file_weight_inst.syntactic_weight}" + mult_note)
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


def display_sonar_info(config: Configuration, contributors: List[Contributor], repo: Repo,
                       file_ownership: Dict[Contributor, List[ContributionDistribution]],
                       project_key: Optional[str]) -> ContributorWeight:
    '''
    Driver function for SonarQube analysis.
    '''

    header(f"{SYNTAX} Syntax + Semantics using SonarQube:", machine_id="sonarqube")

    if not config.use_sonarqube:
        print(f"{INFO} Syntax analysis uses SonarQube and 'config.use_sonarqube = False'. Skipping syntax analysis.")
        return {}

    analysis_running = True
    client = docker.from_env()

    url = f'http://localhost:{config.sonarqube_port}'
    sonar = SonarQubeClient(sonarqube_url=url, username=config.sonarqube_login, password=config.sonarqube_password)

    seconds_waited = 0
    while analysis_running:
        try:
            _ = client.containers.get("mura-sonarqube-scanner-instance")
            print(f"{INFO} Analysis is running. Waiting for it to finish...")
            sleep(2)
            seconds_waited += 2
            if seconds_waited > config.sonarqube_analysis_container_timeout_seconds:
                print(f"{ERROR} SonarQube Analysis is taking too long. Is it stuck/expected?")
                print(f"{INFO} You can increase the timeout with 'config.sonarqube_analysis_container_timeout_seconds' "
                      f"or the --sq-container-exit-timeout flag. You can also inspect the container for errors."
                      f"Current value: {config.sonarqube_analysis_container_timeout_seconds}s.")
                exit(1)
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


def display_semantic_info(tracked_files: List[FileGroup],
                          ownership: Dict[Contributor, List[ContributionDistribution]],
                          semantics: List[List[Tuple[Path, SemanticWeightModel, 'LangElement']]],
                          file_maturity_score: Dict[Path, float]) \
        -> ContributorWeight:
    '''
    Driver function for the semantic analysis.
    '''

    header(f"{SEMANTICS} Semantics:", machine_id="semantics")

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


def display_remote_info(commit_range: CommitRange, repo: Repo, config: Configuration, contributors: List[Contributor]) \
        -> Tuple[RemoteRepository, ContributorWeight]:
    '''
    Driver function for remote repository analysis.
    '''

    header(f"{REMOTE_REPOSITORY} Remote repository management:", machine_id="remote")

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


def display_file_statistics_info(commit_range: CommitRange, contributors: List[Contributor]) \
        -> Dict[Contributor, FlaggedFiles]:
    '''
    Driver function for file statistics (Additions, Deletions, Modifications, Renames etc.)
    '''

    header(f"{FILE_STATS} File statistics", machine_id='file_statistics')

    file_flags = get_flagged_files_by_contributor(commit_range, contributors)
    for contributor in contributors:
        if contributor.name == '?':
            continue
        print(f"{CONTRIBUTOR} {contributor})")
        for key, count in file_flags[contributor].counts.items():
            print(f" => {key} - {count}")
    return file_flags


def get_all_comments(element: LangElement) -> List[LangElement]:
    '''
    Recursively get all comments from a language element - usually a file.
    '''
    comments = []
    for child in element.children:
        if child.kind == 'comment':
            comments.append(child)
        else:
            comments.extend(get_all_comments(child))
    return comments


def display_constructs_info(tracked_files: List[FileGroup],
                            ownership: Dict[Contributor, List[ContributionDistribution]],
                            semantic_analysis_grouped_result: List[
                                List[Tuple[Path, SemanticWeightModel, 'LangElement']]]):
    '''
    Driver function for language constructs analysis.
    '''

    header(f"{SEMANTICS} Constructs:", machine_id="constructs")

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


def display_lines_blanks_comments_info(repository: Repo,
                                       ownership: Dict[Contributor, List[ContributionDistribution]],
                                       semantic_analysis_res: List[
                                           List[Tuple[Path, SemanticWeightModel, 'LangElement']]],
                                       tracked_files: List[FileGroup],
                                       n_extreme_files: int = 5):
    '''
    Driver function for lines, blanks and comments info
    '''

    header(f"{BLANKS_COMMENTS} Blanks and comments:", machine_id="blanks_comments")

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
    '''
    Estimates hours spent on coding based on commit dates, the algorithm is based on git-hours project
    https://github.com/kimmobrunfeldt/git-hours
    :param dates: List of commit dates
    :param max_commit_diff: Maximum time difference between commits to be counted as single coding session
    :param first_commit_addition: Time added to first commit of a session
    '''
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


def display_hour_estimates(contributors: List[Contributor], repository: Repo) -> Dict[Contributor, Tuple[int, int]]:
    '''
    Driver function for hour estimates
    '''

    header(f"{TIME} Hour estimates:", machine_id="hours")

    commits = [x for x in repository.iter_commits()]

    commits_by_author = defaultdict(lambda: [])

    for commit in commits:
        if commit.author.name is None:
            continue
        c = find_contributor(contributors, commit.author.name)
        commits_by_author[c].append(commit.committed_datetime)

    ret: Dict[Contributor, Tuple[int, int]] = {}

    for contributor in contributors:
        if contributor.name == '?' and contributor.email == '?':
            continue
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
    '''
    Computes the estimated weight from the given hours of work based on Normal distribution.

    :param config: Configuration from which to read the base hour match weight
    :param hour_estimate: The expected time put into the project in hours
    :param hours: Estimates as computed from the git-hours algorithm
    '''
    ret: Dict[Contributor, float] = defaultdict(lambda: 0.0)
    header(f"{WEIGHT} Gaussian weights:")
    for contributor, commits_hours in hours.items():
        if contributor.name == '?' and contributor.email == '?':
            continue
        print(f"{CONTRIBUTOR} {contributor.name}:")
        if commits_hours[1] != 0:
            weight = gaussian(config, hour_estimate, commits_hours[1])
            print(f" => {weight:.2f} {WEIGHT} Weight gained for: {commits_hours[1]} hours of work.")
            ret[contributor] += weight
        else:
            print(f" => {INFO} Estimated 0 hours.")

    return ret


def display_summary_info(contributors: List[Contributor],
                         sonar_weights: ContributorWeight,
                         semantic_weights: ContributorWeight,
                         local_syntax: ContributorWeight,
                         repo_management_weights: ContributorWeight,
                         global_rule_weight_multiplier: Dict[Contributor, float],
                         hours: ContributorWeight,
                         file_history_multipliers: Dict[Path, float]) -> None:
    '''
    Prints summary of all the weights and multipliers
    '''
    sums: Dict[Contributor, float] = defaultdict(lambda: 0.0)

    header("Summary:", machine_id="summary")

    def print_section(section: ContributorWeight, add=True):
        if not section:
            print(f'{INFO} Nothing to show here...')
            return

        for contrib in contributors:
            if contrib.name == '?' and contrib.email == '?':
                continue
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
def path_leaf(path: str):
    import ntpath
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def new_file(base_path: Optional[Path], file: str) -> Optional[Path]:
    if not base_path:
        return None
    return Path(str(base_path) + file)


def main(arguments: argparse.Namespace) -> None:
    '''
    The driver function for Mura CLI.

    :param arguments: Arguments passed to the CLI, parsed by `argparse`.
    '''
    config = configuration.validate()

    if arguments.prescan_mode:
        config.prescan_mode = arguments.prescan_mode
    else:
        config.ignore_remote_repo = arguments.ignore_remote_repo
        config.use_sonarqube = not arguments.no_sonarqube
        config.sonarqube_persistent = not arguments.sq_no_persistence
        config.sonarqube_keep_analysis_container = arguments.sq_keep_analysis_container
        config.sonarqube_analysis_container_timeout_seconds = arguments.sq_container_exit_timeout
        config.sonarqube_login = arguments.sq_login
        config.sonarqube_password = arguments.sq_password
        config.sonarqube_port = arguments.sq_port
        config.machine_preprocessed_output = arguments.machine_output
        config.no_graphs = arguments.no_graphs
        

        config.ignore_whitespace_changes = arguments.ignore_whitespace_changes
        config.ignored_extensions = arguments.ignored_extensions

        config.post_validate()

    config.contributor_map = arguments.contributor_map

    repository_path = arguments.repo

    repository = fs_access.validate_repository(repository_path, config)
    commit_range = CommitRange(repository, arguments.head, arguments.root, verbose=True)

    config.anonymous_mode = arguments.anonymous_mode

    contributors = display_contributor_info(commit_range, config)
    separator(section_end=True)

    if config.prescan_mode:
        _, _ = display_commit_info(commit_range, repository, contributors, config)
        separator(section_end=True)
        print(f"{INFO} Pre-scan only mode enabled. Exiting.")
        return

    project_key, container = start_sonar_analysis(config, repository_path)

    tracked_files = get_tracked_files(repository, verbose=True)
    history_analysis_result = commit_range.analyze(verbose=True)
    syntactic_analysis_result = local_syntax_analysis(config, tracked_files)
    file_history_multiplier = file_analyzer.assign_scores(tracked_files, history_analysis_result, config)

    semantic_analysis_grouped_result = semantic_analysis.compute_semantic_weight_result(config, tracked_files,
                                                                                        verbose=True)
    # separator()
    base_file_path = Path(arguments.file).parent if arguments.file else None
    if base_file_path:
        base_file_path = base_file_path / Path(arguments.file).stem
    commit_distribution, insertions_deletions = display_commit_info(commit_range, repository, contributors, config)
    insertions_deletions_info(insertions_deletions, config,
                              output_path=new_file(base_file_path, "_ins-del.png"))
    separator(section_end=True)

    plot_commits([x for x in commit_range][1:], commit_range, contributors, config,
                 output_path=new_file(base_file_path, "_commits.png"))

    _ = display_file_statistics_info(commit_range, contributors)
    separator(section_end=True)

    percentage, ownership = display_percentage_info(history_analysis_result, contributors, config, repository)
    separator(section_end=True)

    display_dir_tree(percentage, repository)
    separator(section_end=True)

    display_lines_blanks_comments_info(repository, ownership, semantic_analysis_grouped_result, tracked_files,
                                       n_extreme_files=5)
    separator(section_end=True)

    header("Unmerged commits", machine_id='unmerged_commits')
    commit_range.display_unmerged_commits_info(repository, config, contributors)
    separator(section_end=True)

    sonar_weights = display_sonar_info(config, contributors, repository, ownership, project_key)
    separator(section_end=True)

    local_syntax_weights = display_local_syntax_info(config, ownership, syntactic_analysis_result, repository,
                                                     file_history_multiplier)
    separator(section_end=True)

    semantic_weights = display_semantic_info(tracked_files, ownership, semantic_analysis_grouped_result,
                                             file_history_multiplier)
    separator(section_end=True)

    display_constructs_info(tracked_files, ownership, semantic_analysis_grouped_result)
    separator(section_end=True)

    hours = display_hour_estimates(contributors, repository)
    hour_weights = gaussian_weights(config, arguments.hour_estimate_per_contributor, hours)
    separator(section_end=True)

    project, repo_management_weights = display_remote_info(commit_range, repository, config, contributors)
    separator(section_end=True)

    global_rule_weight_multiplier = display_rule_info(config, repository, ownership, contributors, project)
    separator(section_end=True)

    display_summary_info(contributors, sonar_weights, semantic_weights, local_syntax_weights, repo_management_weights,
                         global_rule_weight_multiplier, hour_weights, file_history_multiplier)
    separator(section_end=True)


if __name__ == '__main__':
    def contributor_pairs(contributor_map):
        key, value = contributor_map.split(':')
        return key, value


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
    parser.add_argument('--anonymous-mode', action='store_true', default=False,
                        help='Anonymous mode, All contributor names will be replaced with "Contributor #n"')
    parser.add_argument('--no-sonarqube', action='store_true', default=False,
                        help='Do not use SonarQube analysis')
    parser.add_argument('--sq-no-persistence', action='store_true', default=False,
                        help='Use SonarQube in non-persistent mode - data will be stored in the container')
    parser.add_argument('--sq-keep-analysis-container', action='store_true', default=False,
                        help='Keep the analysis container on analysis end, intended for debugging purposes!')
    parser.add_argument('--sq-container-exit-timeout', type=int, default=120, metavar="SECONDS",
                        help='Timeout if the SonarQube analysis takes too long')
    parser.add_argument('--sq-login', type=str, default='admin', metavar="STR",
                        help='SonarQube login')
    parser.add_argument('--sq-password', type=str, default='admin', metavar="STR",
                        help='SonarQube password')
    parser.add_argument('--sq-port', type=int, default=8080, metavar="PORT",
                        help='SonarQube port')
    parser.add_argument('--ignore-whitespace-changes', action='store_false', default=True,
                        help='Ignore whitespace changes in files, whitespace only change will alter line ownership')
    parser.add_argument('--ignored-extensions', type=str, nargs='+', default=[], metavar="EXT",
                        help='Extensions to ignore during analysis')
    parser.add_argument('--ignore-remote-repo', action='store_true', default=False,
                        help='Ignore remote repository, in case of no internet connection or other reasons')
    parser.add_argument('--machine-output', action='store_true', default=False,
                        help='Machine readable output, '
                             'places separators between sections and separators between items in a section')
    parser.add_argument('--no-graphs', action='store_true', default=False,
                        help='Do not display graphs.')
    parser.add_argument('--prescan-mode', action='store_true', default=False,
                        help='Display only pre-scan information, such as contributors and commit range. '
                        'Used for further tuning of the configuration.')

    print(" ".join(sys.argv[1:]))

    args = parser.parse_args()

    # fix argparse contributor-map
    if len(args.contributor_map) > 0:
        args.contributor_map = args.contributor_map[0]

    if args.file != '':
        try:
            with open(args.file, 'w', encoding='UTF-8') as f:
                with redirect_stdout(f):
                    try:
                        main(args)
                    except Exception as inner:
                        header("")
                        print(f"{ERROR} MURA failed to run, please check the following error:")
                        print(inner)
        except Exception as e:
            print(e)
            print(f"Failed to write to file: '{args.file}'")
            sys.exit(1)
    else:
        main(args)
