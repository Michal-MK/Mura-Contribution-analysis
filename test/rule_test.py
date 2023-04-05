import unittest
from pathlib import Path

from git import Repo

from lib import ContributionDistribution, Contributor
from rules import parse_rules
from environment_local import TURTLE_GRAPHICS_REPO


class RuleTests(unittest.TestCase):

    def setUp(self):
        self.repo = Repo(TURTLE_GRAPHICS_REPO)

    def test_rule_no_violations(self):
        rules = parse_rules([r'* "*/Models/" ".*Model.*\.cs" >=1'])

        input = dict()
        input[Contributor("Michal-MK", "michalhz159@gmail.com")] = [
            ContributionDistribution(Path("./TurtleGraphics/Models/IntelliCommandDialogViewModel.cs"), 1),
            ContributionDistribution(Path("./TurtleGraphics/Models/LanguageButtonModel.cs"), 1),
        ]

        result = rules.matches(self.repo, input)
        self.assertFalse(result)
    def test_rule_one_violation(self):
        rules = parse_rules([r'* "*/Models/" "[a-zA-Z_][a-zA-Z0-9_]*Model[a-zA-Z_][a-zA-Z0-9_]*\.cs" >=1'])

        input = dict()
        input[Contributor("Michal-MK", "michalhz159@gmail.com")] = [
            ContributionDistribution(Path("./TurtleGraphics/Models/IntelliCommandDialogView.cs"), 1),
            ContributionDistribution(Path("./TurtleGraphics/Models/LanguageButton.cs"), 1),
        ]

        result = rules.matches(self.repo, input)
        self.assertTrue(result)
        contributor = Contributor("Michal-MK", "michalhz159@gmail.com")
        self.assertTrue(list(result.keys()) == [contributor])

        rule_text = str(result[contributor][0])
        expected_text = "All contributors must have at least 1 file/s matching: " \
                        "`[a-zA-Z_][a-zA-Z0-9_]*Model[a-zA-Z_][a-zA-Z0-9_]*\.cs` " \
                        "in a directory matching: `*/Models`"

        self.assertTrue(rule_text == expected_text)



if __name__ == '__main__':
    unittest.main()
