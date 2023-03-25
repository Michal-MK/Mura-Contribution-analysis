import os
import unittest

from repository_hooks import parse_project


class RepositoryTests(unittest.TestCase):
    def test_connection(self):
        project =  parse_project("https://gitlab.fi.muni.cz/pa165/discord-bot", os.environ['GITLAB_ACCESS_TOKEN'], "")

        self.assertEqual(project.slash_path, "/pa165/discord-bot")
        self.assertEqual(project.access_token, os.environ['GITLAB_ACCESS_TOKEN'])
        self.assertTrue(len(project.issues) == 0)
        self.assertTrue(len(project.members) >= 10)
        self.assertTrue(len(project.pull_requests) == 0)

if __name__ == '__main__':
    unittest.main()
