"""Shard placement for the sample store.

Plain modulo placement: adding or removing a node reshuffles nearly every shard.
"""

SHARDS = 200
NODES = ("store-a", "store-b", "store-c", "store-d")


def place(shard, nodes):
    if not nodes:
        raise ValueError("no nodes")
    return sorted(nodes)[shard % len(nodes)]


def layout(nodes, shards=SHARDS):
    return {shard: place(shard, nodes) for shard in range(shards)}


def moved(before, after):
    """How many shards changed owner between two layouts."""
    return sum(1 for shard, node in before.items() if after.get(shard) != node)


# The placement report reads the current layout straight off the module.
LAYOUT = layout(NODES)
