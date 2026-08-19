import sys


def solve() -> int:
    """
    Read red tile coordinates from input.txt and find the largest rectangle area
    that can be formed using two red tiles as opposite corners.
    
    The area is calculated as (|x1 - x2| + 1) * (|y1 - y2| + 1)
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0
    
    points = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Parse coordinate pair (x, y)
        parts = line.split(',')
        if len(parts) == 2:
            try:
                x = int(parts[0].strip())
                y = int(parts[1].strip())
                points.append((x, y))
            except ValueError:
                continue
    
    if len(points) < 2:
        return 0
    
    max_area = 0
    n = len(points)
    
    for i in range(n):
        x1, y1 = points[i]
        for j in range(i + 1, n):
            x2, y2 = points[j]
            width = abs(x1 - x2) + 1
            height = abs(y1 - y2) + 1
            area = width * height
            if area > max_area:
                max_area = area
    
    return max_area


if __name__ == '__main__':
    print(solve())