import matplotlib.pyplot as plt
from league import absolute_value


def graph(records):
    base_val = absolute_value(records[-1]) // 100 * 100
    plt.plot(
        range(1, len(records) + 1),
        [absolute_value(x) - base_val for x in list(reversed(records))],
    )
    plt.savefig("graph.png")
