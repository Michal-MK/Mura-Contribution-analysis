import re


def parse_data(data_str):
    data = {}
    sums = {}
    lines = data_str.split('\n')
    for line in lines:
        if line.startswith('Anon'):
            line = line.replace('\\', '').strip()
            values = re.split(r'&', line)
            contrib = values[0].strip()
            values = [float(v.strip()) if v.strip() != '-' else float(0) for v in values[1:]]
            data[contrib] = values
        elif line.startswith('Sums:'):
            break
    sum_index = lines.index('Sums:')
    for line in lines[sum_index + 1:]:
        if line.startswith('Anon'):
            contrib, value = line.split(':')
            contrib = contrib.strip()
            value = float(value.strip())
            sums[contrib] = value
    return data, sums


t1 = """
Anon \#1 & - & 33.84 & 6.43 & - & 1.15 & 0.9 \\
Anon \#2 & -106.00 & 35.80 & 8.51 & - & 180.97 & 0.9 \\
Anon \#3 & - & 156.26 & 32.82 & - & 81.90 & 0.9 \\
Anon \#4 & -10.00 & 55.76 & 12.27 & - & 0.00 & 0.9 \\
Sums:
Anon \#1: 37.3
Anon \#2: 123.5
Anon \#3: 243.9
Anon \#4: 52.2
"""

t2 = """
Anon \#1 & -55.00 & 86.00 & 17.50 & - & 81.90 & 0.88 \\
Anon \#2 & - & 37.40 & 8.61 & 50.00 & 0.00 & 0.98 \\
Anon \#3 & -10.00 & 57.20 & 10.45 & 420.00 & 129.82 & 0.98 \\
Anon \#4 & -10.00 & 77.40 & 17.04 & 270.00 & 62.48 & - \\
Sums:
Anon \#1: 121.9
Anon \#2: 94.0
Anon \#3: 594.5
Anon \#4: 418
"""

t3 = """
Anon \#1 & -107.00 & 308.99 & 76.65 & 96.00 & 180.97 & 0.88 \\
Anon \#2 & -407.00 & 288.08 & 70.42 & 544.00 & 180.97 & 0.88 \\
Anon \#3 & -156.00 & 128.56 & 25.98 & 48.00 & 189.57 & 0.88 \\
Anon \#4 & -161.00 & 565.36 & 138.44 & 96.00 & 199.00 & 0.88 \\
Sums:
Anon \#1: 489.0
Anon \#2: 595.2
Anon \#3: 207.8
Anon \#4: 736.6
"""

t4 = """
Anon \#1 & -76.00 & 443.90 & 105.20 & 316.00 & 172.14 & 0.88 \\
Anon \#2 & -485.00 & 1053.70 & 203.63 & 140.00 & 139.49 & 0.88 \\
Anon \#3 & -687.00 & 573.12 & 123.25 & 48.00 & 3.66 & 0.88 \\
Anon \#4 & -61.00 & 471.22 & 102.71 & 128.00 & 196.19 & 0.88 \\
Sums:
Anon \#1: 845.9
Anon \#2: 925.6
Anon \#3: 53.7
Anon \#4: 736.6
"""

t5 = """
Anon \#1 & -70.00 & 57.00 & 14.03 & - & 189.57 & 0.71 \\
Anon \#2 & -100.00 & 228.36 & 55.71 & 272.00 & 195.51 & - \\
Anon \#3 & -96.00 & 20.30 & 4.63 & 160.00 & 0.02 & 0.79 \\
Anon \#4 & -133.00 & 14.35 & 3.03 & - & 0.00 & 0.71 \\
Sums:
Anon \#1: 135.3
Anon \#2: 651.6
Anon \#3: 70.3
Anon \#4: -82.1
"""

t6 = """
Anon \#1 & -53.00 & 75.50 & 15.44 & 70.00 & 0.23 & 0.73 \\
Anon \#2 & -210.00 & 113.56 & 25.74 & 180.00 & 169.67 & 0.81 \\
Anon \#3 & -54.00 & 20.50 & 4.62 & 0.00 & 81.90 & 0.71 \\
Sums:
Anon \#1: 79.0
Anon \#2: 226.0
Anon \#3: 37.6
"""

t7 = """
Anon \#1 & - & 281.31 & 64.16 & 16.00 & 0.23 & 0.98 \\
Anon \#2 & - & 101.70 & 25.78 & 224.00 & 139.49 & 0.79 \\
Anon \#3 & - & 105.21 & 24.90 & 280.00 & 17.26 & 0.88 \\
Anon \#4 & - & 62.34 & 17.91 & 8.00 & 0.00 & 0.71 \\
Sums:
Anon \#1: 354.5
Anon \#2: 387.9
Anon \#3: 376.1
Anon \#4: 62.7
"""

t8 = """
Anon \#1 & -20.00 & 122.20 & 28.27 & - & 29.31 & 0.71 \\
Anon \#2 & -308.00 & 511.81 & 133.20 & - & 196.19 & 0.98 \\
Anon \#3 & -64.00 & 258.50 & 55.72 & - & 1.15 & 0.88 \\
Sums:
Anon \#1: 113.4
Anon \#2: 522.5
Anon \#3: 221.2
"""

t9 = """
Anon \#1 & -105.00 & 20.40 & 4.74 & - & 0.23 & 0.88 \\
Anon \#2 & -35.00 & 146.06 & 34.33 & 128.00 & 101.83 & 0.88 \\
Anon \#3 & -96.00 & 266.25 & 63.80 & 96.00 & 8.79 & 0.98 \\
Anon \#4 & -77.00 & 204.54 & 48.28 & 16.00 & 0.23 & 0.98 \\
Sums:
Anon \#1: -70.0
Anon \#2: 329.8
Anon \#3: 332.0
Anon \#4: 188.2
"""

t10 = """
Anon \#1 & -15.00 & 323.38 & 71.53 & 208.00 & 17.26 & - \\
Anon \#2 & -150.00 & 461.56 & 103.74 & 120.00 & 82.87 & - \\
Anon \#3 & -277.00 & 540.33 & 124.92 & 418.00 & 24.90 & - \\
Anon \#4 & -16.00 & 254.10 & 48.14 & 60.00 & 62.48 & 0.98 \\
Anon \#5 & -26.00 & 380.70 & 77.07 & 40.00 & 139.49 & 0.98 \\
Sums:
Anon \#1: 605.2
Anon \#2: 618.2
Anon \#3: 831.2
Anon \#4: 400.5
Anon \#5: 599.0
"""

t11 = """
Anon \#1 & -45.00 & 363.62 & 95.43 & 300.00 & 82.87 & - \\
Anon \#2 & - & 90.70 & 21.23 & 90.00 & 8.79 & 0.90 \\
Anon \#3 & -75.00 & 139.40 & 36.51 & 126.00 & 121.31 & 0.90 \\
Anon \#4 & -10.00 & 71.42 & 15.99 & 54.00 & 0.23 & 0.81 \\
Sums:
Anon \#1: 797.0
Anon \#2: 189.6
Anon \#3: 313.4
Anon \#4: 106.6
"""

t12 = """
Anon \#1 & -20.00 & 59.90 & 14.22 & 20.00 & 155.76 & 0.88 \\
Anon \#2 & -5.00 & 140.27 & 28.06 & 196.00 & 101.83 & 0.88 \\
Anon \#3 & -30.00 & 95.78 & 21.32 & - & 0.00 & 0.79 \\
Anon \#4 & -125.00 & 81.40 & 13.39 & 80.00 & 0.23 & 0.88 \\
Sums:
Anon \#1: 202.3
Anon \#2: 405.8
Anon \#3: 68.8
Anon \#4: 44.0
"""

t13 = """
Anon \#1 & - & 20.30 & 4.27 & - & 0.00 & 0.71 \\
Anon \#2 & -21.00 & 122.50 & 30.27 & - & 0.00 & 0.88 \\
Anon \#3 & -138.00 & 510.00 & 122.93 & 0.00 & 1.15 & 0.98 \\
Anon \#4 & -9.00 & 207.50 & 46.55 & 8.00 & 1.15 & - \\
Anon \#5 & -8.00 & 202.95 & 44.04 & 8.00 & 81.90 & 0.88 \\
Sums:
Anon \#1: 17.4
Anon \#2: 115.9
Anon \#3: 486.2
Anon \#4: 245.2
Anon \#5: 289.4
"""

t14 = """
Anon \#1 & -42.00 & 318.36 & 72.00 & 60.00 & 189.57 & 0.98 \\
Anon \#2 & -77.00 & 267.50 & 63.61 & 40.00 & 29.31 & 0.88 \\
Anon \#3 & -20.00 & 198.78 & 44.49 & 20.00 & 0.00 & 0.88 \\
Sums:
Anon \#1: 586.0
Anon \#2: 284.6
Anon \#3: 214.1
"""

t15 = """
Anon \#1 & -24.00 & 74.27 & 17.48 & 228.00 & 3.66 & 0.90 \\
Anon \#2 & -219.00 & 178.40 & 44.32 & 168.00 & 29.31 & - \\
Anon \#3 & -15.00 & 180.30 & 42.12 & 200.00 & 8.79 & 0.98 \\
Sums:
Anon \#1: 269.5
Anon \#2: 201.0
Anon \#3: 407.9
"""

t16 = """
Anon \#1 -337.00 & 275.43 & 65.26 & 92.00 & 23.06 & 0.98 \\
Anon \#2 -540.00 & 351.00 & 84.37 & 76.00 & 198.49 & 0.79 \\
Anon \#3 -277.00 & 68.88 & 15.80 & 20.00 & 13.15 & 0.79 \\
Anon \#4 -134.00 & 69.54 & 14.65 & 36.00 & 1.62 & 0.79 \\
Sums:
Anon \#1: 224.9
Anon \#2: 281.0
Anon \#3: -52.6
Anon \#4: 25.6
"""

ts = [
    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t13, t14, t15
]

import matplotlib.pyplot as plt
import numpy as np


def plot_bar_chart(data):
    contrib = list(data.keys())
    sonar = [data[c][0] for c in contrib]
    sem = [data[c][1] for c in contrib]
    syn = [data[c][2] for c in contrib]
    remote = [data[c][3] for c in contrib]
    hours = [data[c][4] for c in contrib]
    rules = [data[c][5] for c in contrib]

    fig, ax = plt.subplots()
    x = np.arange(len(contrib))
    width = 0.1

    ax.bar(x - width * 3, sonar, width=width)
    ax.bar(x - width * 2, sem, width=width)
    ax.bar(x - width * 1, syn, width=width)
    ax.bar(x + width * 0, remote, width=width)
    ax.bar(x + width * 1, hours, width=width)
    ax.bar(x + width * 2, rules, width=width)

    ax.set_xticks(x)
    ax.set_xticklabels(contrib)

    plt.show()


def plot_stacked_bar_chart(data):
    contrib = list(data.keys())
    sonar = [data[c][0] for c in contrib]
    sem = [data[c][1] for c in contrib]
    syn = [data[c][2] for c in contrib]
    remote = [data[c][3] for c in contrib]
    hours = [data[c][4] for c in contrib]
    rules = [data[c][5] for c in contrib]

    fig, ax = plt.subplots()
    x = np.arange(len(contrib))
    width = 0.35

    ax.bar(x - width / 2, sonar, width=width, label='Sonar')
    ax.bar(x - width / 2, sem, bottom=sonar, width=width, label='Sem.')
    ax.bar(x - width / 2, syn, bottom=np.array(sonar) + np.array(sem), width=width, label='Syn.')
    ax.bar(x + width / 2, remote, width=width, label='Remote')
    ax.bar(x + width / 2, hours, bottom=remote, width=width, label='Hours')
    ax.bar(x + width / 2, rules, bottom=np.array(remote) + np.array(hours), width=width, label='Rules')

    ax.set_xticks(x)
    ax.set_xticklabels(contrib)
    ax.legend()

    plt.show()


def create_boxplots(data: list):
    # Extract the data for each column
    sonar = [list(d.values())[0][0] for d in data]
    sem = [list(d.values())[0][1] for d in data]
    syn = [list(d.values())[0][2] for d in data]
    remote = [list(d.values())[0][3] for d in data]
    hours = [list(d.values())[0][4] for d in data]

    # Create a boxplot for each column
    fig, axs = plt.subplots(1, 5, sharey='all', gridspec_kw={'wspace': 0.5})
    axs[0].boxplot(sonar)
    axs[0].set_title('Sonar')
    axs[1].boxplot(sem)
    axs[1].set_title('Sem.')
    axs[2].boxplot(syn)
    axs[2].set_title('Syn.')
    axs[3].boxplot(remote)
    axs[3].set_title('Remote')
    axs[4].boxplot(hours)
    axs[4].set_title('Hours')

    plt.show()


from sklearn.preprocessing import StandardScaler


def create_boxplots_scaled(data: list):
    # Extract the data for each column
    sonar = [list(d.values())[0][0] for d in data]
    sem = [list(d.values())[0][1] for d in data]
    syn = [list(d.values())[0][2] for d in data]
    remote = [list(d.values())[0][3] for d in data]
    hours = [list(d.values())[0][4] for d in data]

    # Normalize the data
    scaler = StandardScaler()
    sonar = scaler.fit_transform(np.array(sonar).reshape(-1, 1)).flatten()
    sem = scaler.fit_transform(np.array(sem).reshape(-1, 1)).flatten()
    syn = scaler.fit_transform(np.array(syn).reshape(-1, 1)).flatten()
    remote = scaler.fit_transform(np.array(remote).reshape(-1, 1)).flatten()
    hours = scaler.fit_transform(np.array(hours).reshape(-1, 1)).flatten()

    # Create a boxplot for each column
    fig, axs = plt.subplots(1, 5, sharey="all", gridspec_kw={'wspace': 0.5})
    axs[0].boxplot(sonar)
    axs[0].set_title('Sonar')
    axs[1].boxplot(sem)
    axs[1].set_title('Sem.')
    axs[2].boxplot(syn)
    axs[2].set_title('Syn.')
    axs[3].boxplot(remote)
    axs[3].set_title('Remote')
    axs[4].boxplot(hours)
    axs[4].set_title('Hours')

    plt.show()


import seaborn as sns


def create_plots(data: list, column: int, col_name: str):
    # Extract the data for the specified column
    values = [list(d.values())[0][column] for d in data]

    # Create a histogram
    plt.figure()
    plt.xlabel("weight points")
    plt.ylabel('Teams')
    plt.hist(values)
    plt.title(f'Histogram of {col_name}')
    for ytick in plt.gca().get_yticks():
        plt.axhline(ytick, color='gray', linestyle='dashed', linewidth=0.5)

    # Create a density plot
    plt.figure()
    plt.xlabel("Weight points")
    plt.ylabel('Density')
    sns.kdeplot(values)
    plt.title(f'Density plot of {col_name}')
    for ytick in plt.gca().get_yticks():
        plt.axhline(ytick, color='gray', linestyle='dashed', linewidth=0.5)

    # Create a bar plot
    plt.figure()
    plt.xlabel("Team #")
    plt.ylabel('Weight points')
    plt.bar(range(len(values)), values)
    plt.title(f'Bar plot of {col_name}')
    for ytick in plt.gca().get_yticks():
        plt.axhline(ytick, color='gray', linestyle='dashed', linewidth=0.5)

    plt.show()


def create_stacked_bar_chart_sum(data: list):
    # Extract the data for each contributor and project
    contributors = sorted(set(k for d in data for k in d.keys()))
    projects = list(range(len(data)))
    sums = [[d.get(contributor, 0) for contributor in contributors] for d in data]

    # Create a stacked bar chart
    plt.figure()
    bottom = [0] * len(projects)
    for i, contributor in enumerate(contributors):
        plt.bar(projects, [sums[project][i] for project in projects], bottom=bottom, label=contributor)
        bottom = [bottom[j] + sums[j][i] for j in range(len(projects))]

    plt.xticks(projects)
    plt.xlabel('Project')
    plt.ylabel('Sum')
    plt.legend()
    plt.ylim(ymin=-250)
    plt.show()


def create_stacked_bar_chart(data: list, colors: list):
    # Extract the data for each contributor and project
    contributors = sorted(set(k for d in data for k in d.keys()))
    projects = list(range(len(data)))
    sums = [[d.get(contributor, 0) for contributor in contributors] for d in data]

    # Sum up all the negative values for each project
    neg_sums = [sum(v for v in d.values() if v < 0) for d in data]

    # Create a stacked bar chart
    plt.figure()
    bottom = [0] * len(projects)

    # Plot the negative sums first
    plt.bar(projects, neg_sums, bottom=bottom)
    bottom = [bottom[j] + neg_sums[j] for j in range(len(projects))]

    # Plot the rest of the data
    for i, contributor in enumerate(contributors):
        name = contributor.replace('\\', '')
        plt.bar(projects, [sums[project][i] for project in projects], bottom=bottom, label=name, color=colors[i])
        bottom = [bottom[j] + sums[j][i] for j in range(len(projects))]

    plt.xticks(projects)
    plt.xlabel('Project')
    plt.ylabel('Sum')
    plt.legend()
    plt.ylim(ymin=-250)
    plt.savefig('stacked_bar_chart.pdf', bbox_inches='tight')
    plt.show()


def create_grouped_bar_chart(data: list):
    # Extract the data for each contributor and project
    contributors = sorted(set(k for d in data for k in d.keys()))
    projects = list(range(len(data)))
    sums = [[d.get(contributor, 0) for contributor in contributors] for d in data]

    # Create a grouped bar chart
    plt.figure()
    bar_width = 0.8 / len(contributors)
    x = np.arange(len(projects))

    # Plot the data for each contributor
    for i, contributor in enumerate(contributors):
        plt.bar(x + i * bar_width, [sums[project][i] for project in projects], width=bar_width, label=contributor)

    plt.xticks(x + (len(contributors) - 1) * bar_width / 2, projects)
    plt.xlabel('Project')
    plt.ylabel('Sum')
    plt.legend()
    plt.show()


def create_overlayed_line_chart(data: list, ids: list):
    # Extract the data for each contributor and project
    contributors = sorted(set(k for d in data for k in d.keys()))
    projects = list(range(len(data)))

    # Sort the contributors within each project by their values
    sorted_data = []
    for d in data:
        sorted_contributors = sorted(d.items(), key=lambda x: x[1], reverse=True)
        sorted_data.append({f'Anon {i + 1}': v for i, (_, v) in enumerate(sorted_contributors)})

    # Scale the data to the 0-1 range
    min_sum = -121.1
    max_sum = 1012.35
    scaled_data = [{k: (v - min_sum) / (max_sum - min_sum) for k, v in d.items()} for d in sorted_data]

    # Create an overlayed line chart
    plt.figure(figsize=(8.2, 6))

    # Plot the data for each project
    for i, project in enumerate(projects):
        x = list(scaled_data[i].keys())
        y = list(scaled_data[i].values())
        plt.plot(x, y, label=f'Project {ids[i]}', alpha=0.5)

    # add horizontal lines for each tenth

    for i in range(11):
        plt.axhline(i/10, color='gray', linestyle='dashed', linewidth=0.5)

    plt.xlabel('Contributor')
    plt.ylabel('Scaled Sum')
    plt.subplots_adjust(right=0.8)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.savefig('line_chart.pdf', bbox_inches='tight')
    plt.show()


parsed_data_vals = [x[0] for x in [parse_data(y) for y in ts]]
parsed_data_sums = [x[1] for x in [parse_data(y) for y in ts]]

airports = [parsed_data_sums[0], parsed_data_sums[4], parsed_data_sums[6], parsed_data_sums[9], parsed_data_sums[13]]
barber = [parse_data(t16)[1]]

# create_boxplots(parsed_data_vals)

create_overlayed_line_chart(airports + barber, [1, 5, 7, 10, 14, 99])
#
# create_grouped_bar_chart(parsed_data_sums)
#
create_stacked_bar_chart(parsed_data_sums, ['red', 'green', 'blue', 'orange', 'purple'])
#
# create_plots(parsed_data_vals, 0, 'SonarQube analysis')
# create_plots(parsed_data_vals, 1, 'Semantics')
# create_plots(parsed_data_vals, 2, 'Syntax')
# create_plots(parsed_data_vals, 3, 'Repo')
# create_boxplots_scaled(parsed_data_vals)


# for t in ts:
#     data, sums = parse_data(t)
#     plot_bar_chart(data)

contribs = [37, 123, 243, 52, 121, 94, 494, 418, 489, 595, 207, 736, 845, 925, 53, 736, 135, 651, 70, -82, 79, 226, 37,
            354, 387, 376, 62, 113, 522, 221, -70, 329, 332, 188, 605, 618, 831, 400, 599, 797, 189, 313, 106, 202, 405,
            68, 44, 17, 115, 486, 245, 289, 586, 284, 214, 269, 201, 407]

# show boxplot for contribs

plt.boxplot(contribs)

plt.title('Boxplot of obtained weights')
plt.axhline(np.median(contribs), color='orange', linestyle='dashed', linewidth=1)
plt.text(1.40, np.median(contribs) + 40, np.median(contribs))

# display the value of the first and third quartile
plt.axhline(np.percentile(contribs, 75), color='g', linestyle='dashed', linewidth=1)
plt.text(0.55, np.percentile(contribs, 75) - 68, np.percentile(contribs, 75))
plt.axhline(np.percentile(contribs, 25), color='g', linestyle='dashed', linewidth=1)
plt.text(0.55, np.percentile(contribs, 25) + 40, np.percentile(contribs, 25))

# display the outliers (largest and smallest value)

plt.axhline(np.max(contribs), color='r', linestyle='dashed', linewidth=1)
plt.text(0.55, np.max(contribs) - 68, np.max(contribs))

plt.axhline(np.min(contribs), color='r', linestyle='dashed', linewidth=1)
plt.text(0.55, np.min(contribs) + 40, np.min(contribs))

top_outlier_diff = np.max(contribs) - np.percentile(contribs, 75)
bottom_outlier_diff = np.percentile(contribs, 25) - np.min(contribs)

# display the outliers 1.5 times the interquartile range in both directions

plt.axhline(np.max(contribs) + 0.2 * top_outlier_diff, color='b', linestyle='dashed', linewidth=1)
plt.text(0.55, np.max(contribs) + 0.2 * top_outlier_diff + 40, np.max(contribs) + 0.2 * top_outlier_diff)

plt.axhline(np.min(contribs) - 0.2 * bottom_outlier_diff, color='b', linestyle='dashed', linewidth=1)
plt.text(0.55, np.min(contribs) - 0.2 * bottom_outlier_diff - 68, np.min(contribs) - 0.2 * bottom_outlier_diff)

# set the y-axis limits
plt.ylim(-250, 1250)

plt.savefig('boxplot.pdf', bbox_inches='tight')
plt.show()
