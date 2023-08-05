from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List

from matplotlib import pyplot as plt
from matplotlib.dates import DateFormatter, drange, date2num

from configuration import Configuration
from history_analyzer import CommitRange
from lib import Contributor
from uni_chars import INFO


def plot_commits(commits: List[str], commit_range: CommitRange, contributors: List[Contributor],
                 config: Configuration,
                 force_x_axis_dense_labels=False, output_path: Optional[Path] = None) -> None:
    '''
    Plotting function for commit distribution
    '''

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
        if not config.no_graphs:
            plt.show()
