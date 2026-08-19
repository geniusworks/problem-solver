from typing import List, Dict
import sys
from collections import defaultdict


def solve() -> int:
    """
    Count the number of different paths from 'you' to 'out' in a DAG.
    
    Each line is of the form: device_name: target1 target2 ...
    We need to count all paths from 'you' to 'out'.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0
    
    # Build the graph
    graph: Dict[str, List[str]] = defaultdict(list)
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse the line: "name: target1 target2 ..."
        if ':' not in line:
            continue
        
        parts = line.split(':', 1)
        device_name = parts[0].strip()
        targets_str = parts[1].strip()
        
        if targets_str:
            targets = targets_str.split()
            graph[device_name].extend(targets)
    
    # Count paths from 'you' to 'out' using memoization
    # Since this is a DAG (data flows forward only), we can use DFS with memoization
    
    def count_paths(node: str, memo: Dict[str, int]) -> int:
        if node in memo:
            return memo[node]
        
        if node == 'out':
            memo[node] = 1
            return 1
        
        total = 0
        for neighbor in graph[node]:
            total += count_paths(neighbor, memo)
        
        memo[node] = total
        return total
    
    memo: Dict[str, int] = {}
    result = count_paths('you', memo)
    
    return result


if __name__ == '__main__':
    print(solve())