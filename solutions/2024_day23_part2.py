import sys


def solve() -> str:
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return ""
    
    # Parse edges and build adjacency set
    edges = []
    nodes = set()
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '-' not in line:
            continue
        parts = line.split('-')
        if len(parts) != 2:
            continue
        a, b = parts[0].strip(), parts[1].strip()
        if not a or not b:
            continue
        edges.append((a, b))
        nodes.add(a)
        nodes.add(b)
    
    if not nodes:
        return ""
    
    # Build adjacency sets
    adj = {node: set() for node in nodes}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    
    # Map node names to indices
    node_list = sorted(nodes)
    n = len(node_list)
    node_to_idx = {node: i for i, node in enumerate(node_list)}
    
    # Build adjacency as list of sets of indices
    adj_idx = [set() for _ in range(n)]
    for a, b in edges:
        ia = node_to_idx[a]
        ib = node_to_idx[b]
        adj_idx[ia].add(ib)
        adj_idx[ib].add(ia)
    
    # Find maximum clique using Bron-Kerbosch algorithm with pivot
    max_clique = []
    
    def bron_kerbosch(r, p, x):
        nonlocal max_clique
        
        # If P and X are both empty, we have a maximal clique
        if not p and not x:
            if len(r) > len(max_clique):
                max_clique = list(r)
            return
        
        # Choose pivot from P ∪ X
        pivot_set = p | x
        if not pivot_set:
            if len(r) > len(max_clique):
                max_clique = list(r)
            return
        
        # Pick a pivot (the one with most neighbors in P)
        pivot = max(pivot_set, key=lambda v: len(adj_idx[v] & p))
        
        # For each vertex in P that is not adjacent to the pivot
        candidates = [v for v in p if v not in adj_idx[pivot]]
        
        for v in candidates:
            r.add(v)
            p_new = p & adj_idx[v]
            x_new = x & adj_idx[v]
            bron_kerbosch(r, p_new, x_new)
            r.remove(v)
            p.remove(v)
            x.add(v)
    
    # Initialize and run Bron-Kerbosch
    r = set()
    p = set(range(n))
    x = set()
    bron_kerbosch(r, p, x)
    
    if not max_clique:
        # If no clique found (shouldn't happen if there are nodes), return the lexicographically smallest single node
        return node_list[0]
    
    # Convert indices back to node names and sort alphabetically
    clique_nodes = sorted([node_list[i] for i in max_clique])
    
    return ",".join(clique_nodes)


if __name__ == '__main__':
    result = solve()
    print(result)