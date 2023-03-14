import unittest

import git

from history_analyzer import CommitRange
from lib import get_tracked_files, set_repo
from mura import merge_results
from semantic_analysis import compute_semantic_weight_grouped
from test.environment import TWO_CONTRIB_REPO


class IntegrationTest(unittest.TestCase):

    def test_integration_one(self):
        repo = git.Repo(TWO_CONTRIB_REPO)
        set_repo(repo)
        # TODO branch and tag name support
        range = CommitRange("HEAD", "c1c8eb0afaa9cec949b1601720d66fe4b6bcce31", repo)
        result = range.analyze()
        tracked_files = get_tracked_files(repo)
        weights = []
        for tf in tracked_files:
            sem_w = compute_semantic_weight_grouped(tf)
            weights.append(sem_w)
        merge_results(result, tracked_files, weights)


if __name__ == '__main__':
    unittest.main()