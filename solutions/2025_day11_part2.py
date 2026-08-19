import sys
from typing import List, Dict, Set, Tuple
from collections import defaultdict

def solve() -> int:
    """
    Read a directed graph from input.txt and count the number of paths from 'svr' to 'out'
    that visit both 'dac' and 'fft'.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(0)
        return 0

    # Parse the graph
    graph: Dict[str, List[str]] = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Each line is in the format: "node: neighbor1 neighbor2 ..."
        if ':' not in line:
            continue
        parts = line.split(':', 1)
        if len(parts) != 2:
            continue
        node = parts[0].strip()
        neighbors_str = parts[1].strip()
        if neighbors_str:
            neighbors = neighbors_str.split()
            graph[node] = neighbors
        else:
            graph[node] = []

    # Use DP with memoization: state is (current_node, visited_dac, visited_fft)
    # Since the graph is a DAG (no cycles in practice), we can use memoization effectively.
    # But to be safe, we'll use a visited set to avoid cycles, though the problem implies DAG.
    # Actually, for large graphs, memoization on (node, seen_dac, seen_fft) works if the graph is a DAG.
    # Let's use DFS with memoization.
    
    memo = {}
    
    def dfs(current: str, seen_dac: bool, seen_fft: bool) -> int:
        """
        Returns the count of valid paths from current to 'out' 
        given whether dac and fft have been seen.
        """
        if current == 'out':
            return 1 if (seen_dac and seen_fft) else 0
        
        state = (current, seen_dac, seen_fft)
        if state in memo:
            return memo[state]
        
        count = 0
        neighbors = graph.get(current, [])
        for neighbor in neighbors:
            new_seen_dac = seen_dac or (neighbor == 'dac')
            new_seen_fft = seen_fft or (neighbor == 'fft')
            count += dfs(neighbor, new_seen_dac, new_seen_fft)
        
        memo[state] = count
        return count

    # Start DFS from 'svr'
    initial_seen_dac = ('svr' == 'dac')
    initial_seen_fft = ('svr' == 'fft')
    
    result = dfs('svr', initial_seen_dac, initial_seen_fft)
    print(result)
    return result

if __name__ == '__main__':
    solve()