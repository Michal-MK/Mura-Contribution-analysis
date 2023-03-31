import datetime
import os
import unittest

from repository_hooks import parse_project


class RepositoryTests(unittest.TestCase):
    def test_connection(self):
        project =  parse_project("https://gitlab.fi.muni.cz/pa165/discord-bot", os.environ['GITLAB_ACCESS_TOKEN'], "")

        self.assertEqual(project.path, "/pa165/discord-bot")
        self.assertEqual(project.access_token, os.environ['GITLAB_ACCESS_TOKEN'])
        self.assertTrue(len(project.issues) == 0)
        self.assertTrue(len(project.members) >= 10)
        self.assertTrue(len(project.pull_requests) == 0)

    def test_student_project(self):
        project = parse_project("https://gitlab.fi.muni.cz/xstys/airport-manager", os.environ['GITLAB_ACCESS_TOKEN'], "")

        self.assertEqual(project.path, "/xstys/airport-manager")
        self.assertEqual(project.access_token, os.environ['GITLAB_ACCESS_TOKEN'])

        F = '%Y-%m-%dT%H:%M:%S.%f%z'

        expected = [
            'Kryštof-Mikuláš Štys', 'Matěj Gorgol', 'Jan Sýkora', 'Tomáš Tomala', 'Tereza Vrabcová', 'Michal Hazdra'
        ]

        creation_date = datetime.datetime.strptime('2023-03-04T21:05:38.132+01:00', F)

        issues = [x for x in project.issues]

        self.assertTrue(len(issues) >= 10)

        an_issue = list(filter(lambda x: datetime.datetime.strptime(x.created_at, F) == creation_date, issues))[0]

        self.assertTrue(an_issue.name == "Steward service")
        self.assertTrue(an_issue.description == "- [x] CRUD ops")
        self.assertTrue(an_issue.author == "Kryštof-Mikuláš Štys")
        self.assertTrue(an_issue.state == "closed")

        members = [x for x in project.members]

        for member in members:
            self.assertTrue(member in expected)

        merge = datetime.datetime.strptime('2023-03-26T23:53:23.108+02:00', F)
        prs = [x for x in project.pull_requests]

        def filter_lambda(x):
            return datetime.datetime.strptime(x.merged_at, F) == merge if x.merged_at is not None else False

        a_merge = list(filter(filter_lambda, prs))[0]

        self.assertTrue(a_merge.name == 'Steward extended testing')
        self.assertTrue(a_merge.description == '')
        self.assertTrue(a_merge.author == 'Kryštof-Mikuláš Štys')
        self.assertTrue(a_merge.merged_by == 'Kryštof-Mikuláš Štys')
        self.assertTrue(a_merge.merge_status == 'can_be_merged')
        self.assertTrue(a_merge.target_branch == 'develop')
        self.assertTrue(a_merge.source_branch == 'steward-extended-testing')
        self.assertTrue(len(a_merge.commit_shas) == 13)
        self.assertTrue('1334ac63c04167b7126b2a48a74204af52571247' in a_merge.commit_shas)
        self.assertTrue(len(a_merge.reviewers) == 4)
        self.assertTrue('Matěj Gorgol' in a_merge.reviewers)
        self.assertTrue('Jan Sýkora' in a_merge.reviewers)
        self.assertTrue('Tomáš Tomala' in a_merge.reviewers)
        self.assertTrue('Tereza Vrabcová' in a_merge.reviewers)



if __name__ == '__main__':
    unittest.main()
