from typing import List
import sys

def find_word(grid):
    directions = [(0, 1), (1, 0), (1, 1), (-1, -1)] # Right, Down, Diagonal and Antidiagonal direction vectors
    words = ['XMAS', 'SAMX'] # Words to be searched
    count = 0
    
    for word in words:
        word_len = len(word)
        grid_height = len(grid)
        grid_width = len(grid[0])
        
        for x in range(grid_height):
            for y in range(grid_width):
                for dx, dy in directions:
                    match = True
                    for i in range(word_len):
                        nx, ny = x + i * dx, y + i * dy
                        if nx < 0 or nx >= grid_height or ny < 0 or ny >= grid_width or grid[nx][ny] != word[i]:
                            match = False
                            break
                    if match:
                        count += 1
    return count

def solve() -> int:
    try:
        with open('input.txt') as f:
            lines = [line.strip() for line in f]
            
            grid = []
            for line in lines:
                row = [ch for ch in line if ch != '.']
                grid.append(row)
                
    except FileNotFoundError:
        sys.exit("Input file not found.")
        
    return find_word(grid)

if __name__ == '__main__':
    print(solve())