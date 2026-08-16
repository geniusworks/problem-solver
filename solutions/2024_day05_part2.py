from collections import defaultdict, deque

def solve() -> int:
    with open('input.txt') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # Parse rules and updates
    rules = set()
    updates = []
    
    i = 0
    # Read rules until empty line
    while i < len(lines) and lines[i]:
        if '|' in lines[i]:
            a, b = map(int, lines[i].split('|'))
            rules.add((a, b))
        else:
            # This is an update line
            break
        i += 1
    
    # Skip empty line
    i += 1
    
    # Read updates
    while i < len(lines):
        update = list(map(int, lines[i].split(',')))
        updates.append(update)
        i += 1
    
    def is_correct_order(update, rules):
        """Check if update follows all ordering rules"""
        page_positions = {page: i for i, page in enumerate(update)}
        
        for a, b in rules:
            if a in page_positions and b in page_positions:
                if page_positions[a] >= page_positions[b]:
                    return False
        return True
    
    def topological_sort(pages, rules):
        """Sort pages according to the rules using topological sort"""
        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all pages
        for page in pages:
            if page not in in_degree:
                in_degree[page] = 0
        
        # Build graph from rules
        for a, b in rules:
            if a in pages and b in pages:  # Only consider rules relevant to this update
                graph[a].append(b)
                in_degree[b] += 1
        
        # Kahn's algorithm
        queue = deque([page for page in pages if in_degree[page] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return result
    
    total_sum = 0
    
    for update in updates:
        if not is_correct_order(update, rules):
            # This update needs to be corrected
            corrected = topological_sort(update, rules)
            
            # Get middle element (1-indexed)
            middle_index = len(corrected) // 2
            total_sum += corrected[middle_index]
    
    return total_sum

if __name__ == '__main__':
    print(solve())