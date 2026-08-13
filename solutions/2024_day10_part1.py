from typing import List
import sys
from collections import deque

def solve() -> int:
    with open('input.txt') as f:
        grid = [line.strip() for line in f]
    
    rows, cols = len(grid), len(grid[0])
    
    def find_hiking_trails(start):
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        visited = [[False] * cols for _ in range(rows)]
        
        queue = deque([start])
        visited[start[0]][start[1]] = True
        reachable_nines = set()
        
        while queue:
            x, y = queue.popleft()
            
            if grid[x][y] == '9':
                reachable_nines.add((x, y))
            
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < rows and 0 <= ny < cols and not visited[nx][ny] and grid[nx][ny] == str(int(grid[x][y]) + 1):
                    queue.append((nx, ny))
                    visited[nx][ny] = True
        
        return len(reachable_nines)
    
    def calculate_total_score():
        total_score = 0
        for i in range(rows):
            for j in range(cols):
                if grid[i][j] == '0':
                    total_score += find_hiking_trails((i, j))
        
        return total_score
    
    return calculate_total_score()

if __name__ == '__main__':
    print(solve())