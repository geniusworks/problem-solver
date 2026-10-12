import sys
from collections import defaultdict


def solve() -> int:
    """
    Read the network map from input.txt, find all triangles (sets of three
    mutually connected computers), and count how many contain at least one
    computer whose name starts with 't'.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return 0

    # Build the undirected graph
    graph = defaultdict(set)

    for line in lines:
        # Each line is of the form "ab-cd"
        if '-' not in line:
            continue
        parts = line.split('-')
        if len(parts) != 2:
            continue
        u, v = parts[0].strip(), parts[1].strip()
        if not u or not v:
            continue
        graph[u].add(v)
        graph[v].add(u)

    # Collect all unique nodes
    nodes = sorted(graph.keys())

    # Find all triangles using the u < v < w ordering to avoid duplicates
    # For each edge (u, v) where u < v, find common neighbors w > v
    count = 0
    for i, u in enumerate(nodes):
        for j in range(i + 1, len(nodes)):
            v = nodes[j]
            if v not in graph[u]:
                continue
            # u and v are connected, and u < v
            # Find common neighbors w such that w > v
            common = graph[u] & graph[v]
            for w in common:
                if w > v:
                    # Triangle (u, v, w) with u < v < w
                    if u.startswith('t') or v.startswith('t') or w.startswith('t'):
                        count += 1

    return count


if __name__ == '__main__':
    print(solve())