import unittest
from pathlib import Path

import gitlab

from configuration import Configuration

class RepositoryTests(unittest.TestCase):
    def test_connection(self):
        config = Configuration.load_from_file(Path("configuration_data/configuration.txt"),
                                              Path("rule_data/rules.txt"),
                                              Path("remotes_data/repositories.txt"))
        gl = gitlab.Gitlab('https://gitlab.fi.muni.cz', private_token=config.access_token)
        gl.auth()

        first_project = config.projects[0]
        issues = first_project.get_issues()

        self.assertIsNotNone(issues)


if __name__ == '__main__':
    unittest.main()
