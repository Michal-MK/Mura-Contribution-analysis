import unittest
from contextlib import redirect_stdout
from pathlib import Path

import git

from configuration import Configuration
from history_analyzer import CommitRange
from lib import get_tracked_files, set_repo
from mura import merge_results
from semantic_analysis import compute_semantic_weight_grouped
from environment_local import TWO_CONTRIB_REPO


class IntegrationTest(unittest.TestCase):

    def test_integration_one(self):
        repo = git.Repo(TWO_CONTRIB_REPO)
        set_repo(repo)
        range = CommitRange("HEAD", "c1c8eb0afaa9cec949b1601720d66fe4b6bcce31", repo)
        config = Configuration.load_from_file(Path("configuration_data/configuration.txt"),
                                              Path("rule_data/rules.txt"))
        result = range.analyze()
        tracked_files = get_tracked_files(repo)
        weights = []
        for tf in tracked_files:
            sem_w = compute_semantic_weight_grouped(tf)
            weights.append(sem_w)

        merge_results(repo, range, result, tracked_files, weights, config)


    def test_integration_two(self):
        BASE = Path(r"C:\MUNI\last\Java\M1")
        r1 = BASE / "airport-manager"
        r2 = BASE / "pa165_language_school"
        r3 = BASE / "pa165-formula-one-team"
        r4 = BASE / "pa165-movie-recommendation-project"
        r5 = BASE / "pa165-team-delta"

        repos = [r1, r2, r3, r4, r5]

        for r in repos:
            with open("./" + r.name + ".txt", "w", encoding='UTF-8') as f:
                with redirect_stdout(f):
                    repo = git.Repo(r)
                    set_repo(repo)
                    range = CommitRange("HEAD", "ROOT", repo)
                    config = Configuration.load_from_file(Path("configuration_data/configuration.txt"),
                                                          Path("rule_data/rules.txt"))
                    result =  range.analyze()
                    tracked_files = get_tracked_files(repo)
                    weights = []
                    for tf in tracked_files:
                        sem_w = compute_semantic_weight_grouped(tf)
                        weights.append(sem_w)

                    merge_results(repo, range, result, tracked_files, weights, config)

if __name__ == '__main__':
    unittest.main()
