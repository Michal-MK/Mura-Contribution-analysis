import matplotlib.pyplot as plt
import seaborn as sns
from numpy import average

data = [28, 15, 20, 20, 19, 29, 21, 18, 18, 16, 13, 15, 13, 12, 13, 15, 21, 16, 30,
        16, 17, 17, 24, 25, 15, 14, 22, 20, 27, 25, 18, 28, 19, 14, 32, 49, 26, 12,
        32, 31, 32, 32, 22, 15, 28, 27, 27, 18, 30, 31, 23, 36, 27, 18, 35, 20, 45,
        25, 19, 20, 21, 22, 46, 14, 30, 15, 30, 22, 25, 18, 20, 15, 15, 28, 30, 25,
        15, 18, 22, 19, 18, 18, 25, 34, 21, 21, 21, 21, 25, 21, 22, 14, 30, 27, 30,
        22, 27, 22, 14, 30, 33, 26, 22, 30, 44, 27, 23, 35, 21, 40, 40, 35]

# plt.hist(data, bins=20)
# # plot line for the mean
# plt.axvline(sum(data) / len(data), color='k', linestyle='dashed', linewidth=1)
# plot average
print(len(data))
plot = sns.histplot(data, kde=True, bins=16)
plot.set_xlabel("# lines changed")
plot.set_ylabel("# files")
plt.ylim(0, 20)
plt.show()

dead_code = 14
live_code = []
for p in data:
    code = p - dead_code
    live_code.append(code)

print(average(live_code))
print(average(data))