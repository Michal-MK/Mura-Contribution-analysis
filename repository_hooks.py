import gitlab
import urllib3.util

from test.environment import GITLAB_TOKEN

PROJECTS = [
    # 'https://gitlab.fi.muni.cz/xwehrenb/pa165-movie-recommendation-project',
    'https://gitlab.fi.muni.cz/xgulcik/pa165-formula-one-team',
    'https://gitlab.fi.muni.cz/xstys/airport-manager'
]

PROJECT_IDS = [
    '29550',
    '29600'
]

if __name__ == '__main__':
    gl = gitlab.Gitlab('https://gitlab.fi.muni.cz', private_token=GITLAB_TOKEN)
    url1 = urllib3.util.parse_url(PROJECTS[0])
    path = url1.path
    gl.auth()
    project = gl.projects.get(PROJECT_IDS[1])
    for issue in project.issues.list(iterator=True):
        print(issue)

    for mr in project.mergerequests.list(iterator=True):
        print(mr)

    group = gl.groups.get('pa165')
    for member in group.members.list(iterator=True):
        print(member.name)
    for proj in group.projects.list(iterator=True):
        print(proj.name)
