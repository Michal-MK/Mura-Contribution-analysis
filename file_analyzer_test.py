import xmlrpc.client
from pathlib import Path

from file_analyzer import get_tracked_files, compute_file_weight, has_weight_map

# TODO temp
repos_path = "C:\\MUNI\\xth. semester\\sdipr\src\\repositories"
single_commit = repos_path + "\\single_commit"
tg = "C:\\Repositories\\TurtleGraphics\\"

single_file = r'C:\MUNI\xth. semester\sdipr\src\repositories\single_file\NasModel.cs'

if __name__ == '__main__':
    tracked_files = get_tracked_files(Path(tg))
    weights = []
    for file_group in tracked_files:
        for file in file_group.files:
            print(file_group.name)
            if has_weight_map(file):
                weight = compute_file_weight(file)
                print(f"{file}: {weight.average_line_weight}")
                weights.append(weight)
    print(f"Average weight: {sum(x.average_line_weight for x in weights) / len(weights)}")
    max_w = max(weights, key=lambda x: x.total_line_weight)
    print(f"Highest weight {max_w.file}: {max_w.average_line_weight} / {max_w.maximum_achievable_line_weight}")
    min_w = min(weights, key=lambda x: x.total_line_weight)
    print(f"Lowest weight {min_w.file}: {min_w.average_line_weight} / {min_w.maximum_achievable_line_weight}")

    file_weight = compute_file_weight(Path(single_file))
    print(file_weight.average_line_weight)
    print(file_weight.total_line_weight)
    print(file_weight.maximum_achievable_line_weight)
