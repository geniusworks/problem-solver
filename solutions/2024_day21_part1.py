from functools import lru_cache
import sys

# keypad layouts
NUM_POS = {
    '7': (0, 0), '8': (0, 1), '9': (0, 2),
    '4': (1, 0), '5': (1, 1), '6': (1, 2),
    '1': (2, 0), '2': (2, 1), '3': (2, 2),
    '0': (3, 1), 'A': (3, 2),
}
DIR_POS = {
    '^': (0, 1), 'A': (0, 2),
    '<': (1, 0), 'v': (1, 1), '>': (1, 2),
}

MOVES = {
    '^': (-1, 0),
    'v': (1, 0),
    '<': (0, -1),
    '>': (0, 1),
}
REV_MOVE = {v: k for k, v in MOVES.items()}

def build_adj(pos):
    adj = {k: [] for k in pos}
    for k1, p1 in pos.items():
        for k2, p2 in pos.items():
            if k1 == k2:
                continue
            dr = p2[0] - p1[0]
            dc = p2[1] - p1[1]
            if (dr, dc) in MOVES.values():
                adj[k1].append(k2)
    return adj

NUM_ADJ = build_adj(NUM_POS)
DIR_ADJ = build_adj(DIR_POS)

def bfs_all_shortest(adj, start, goal):
    from collections import deque
    dist = {node: None for node in adj}
    parents = {node: [] for node in adj}
    q = deque([start])
    dist[start] = 0
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] is None:
                dist[v] = dist[u] + 1
                parents[v].append(u)
                q.append(v)
            elif dist[v] == dist[u] + 1:
                parents[v].append(u)
    if dist[goal] is None:
        return []
    # reconstruct all shortest paths as list of node sequences
    paths = []
    def rec(node, cur):
        if node == start:
            paths.append(list(reversed(cur + [start])))
            return
        for p in parents[node]:
            rec(p, cur + [node])
    rec(goal, [])
    return paths, dist[goal]

def shortest_symbol_paths(pos, adj):
    # returns dict[(a,b)] -> list of symbol lists (controller symbols)
    symbols = list(pos.keys())
    paths = {}
    for a in symbols:
        for b in symbols:
            if a == b:
                # zero moves, just press A
                paths[(a, b)] = [['A']]
                continue
            node_paths, d = bfs_all_shortest(adj, a, b)
            sym_paths = []
            for np in node_paths:
                # np is list of nodes from a to b
                syms = []
                for i in range(len(np) - 1):
                    p1 = pos[np[i]]
                    p2 = pos[np[i + 1]]
                    dr = p2[0] - p1[0]
                    dc = p2[1] - p1[1]
                    syms.append(REV_MOVE[(dr, dc)])
                syms.append('A')
                sym_paths.append(syms)
            paths[(a, b)] = sym_paths
    return paths

NUM_PATHS = shortest_symbol_paths(NUM_POS, NUM_ADJ)
DIR_PATHS = shortest_symbol_paths(DIR_POS, DIR_ADJ)

# quick distance for depth 1
def dist_from_paths(paths):
    d = {}
    for (a, b), lst in paths.items():
        if not lst:
            d[(a, b)] = None
        else:
            d[(a, b)] = min(len(p) for p in lst)
    return d

NUM_DIST = dist_from_paths(NUM_PATHS)
DIR_DIST = dist_from_paths(DIR_PATHS)

@lru_cache(maxsize=None)
def cost(a, b, keypad, depth):
    # keypad: 'num' or 'dir'
    if depth == 1:
        if keypad == 'num':
            return NUM_DIST[(a, b)]
        else:
            return DIR_DIST[(a, b)]
    # get paths for this keypad
    if keypad == 'num':
        paths = NUM_PATHS.get((a, b), [])
    else:
        paths = DIR_PATHS.get((a, b), [])
    if not paths:
        return 10**18
    best = 10**18
    for p in paths:
        total = 0
        prev = 'A'
        # typing the path symbols using directional keypad with depth-1
        for sym in p:
            # cost to go from prev to sym on directional keypad
            c = cost(prev, sym, 'dir', depth - 1)
            total += c
            prev = sym
        if total < best:
            best = total
    return best

def total_presses(code, depth=3):
    prev = 'A'
    total = 0
    for ch in code:
        total += cost(prev, ch, 'num', depth)
        prev = ch
    return total

def solve() -> int:
    try:
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(0)
        return 0
    total_complexity = 0
    for code in lines:
        if not code.endswith('A'):
            continue
        numeric_part = int(code[:-1]) if code[:-1] else 0
        presses = total_presses(code, depth=3)
        total_complexity += presses * numeric_part
    print(total_complexity)

if __name__ == '__main__':
    solve()