import re
import sys

def solve() -> int:
    """
    Read robot positions and velocities from input.txt, simulate their movement
    for 100 seconds in a 101x103 grid, and compute the safety factor.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise

    # Grid dimensions
    W = 101
    H = 103
    t = 100

    # Parse robots
    robots = []
    for line in lines:
        # Match pattern: p=x,y v=x,y
        match = re.match(r'p=(-?\d+),(-?\d+)\s+v=(-?\d+),(-?\d+)', line)
        if match:
            px = int(match.group(1))
            py = int(match.group(2))
            vx = int(match.group(3))
            vy = int(match.group(4))
            robots.append((px, py, vx, vy))

    # Calculate positions after t seconds
    mid_x = W // 2  # 50
    mid_y = H // 2  # 51

    # Quadrant counts
    top_left = 0
    top_right = 0
    bottom_left = 0
    bottom_right = 0

    for px, py, vx, vy in robots:
        # Calculate position after t seconds with wrapping
        x = (px + vx * t) % W
        y = (py + vy * t) % H

        # Determine quadrant
        # Middle column: x == mid_x (50)
        # Middle row: y == mid_y (51)
        if x < mid_x:
            if y < mid_y:
                top_left += 1
            elif y > mid_y:
                bottom_left += 1
            # y == mid_y: excluded
        elif x > mid_x:
            if y < mid_y:
                top_right += 1
            elif y > mid_y:
                bottom_right += 1
            # y == mid_y: excluded
        # x == mid_x: excluded

    safety_factor = top_left * top_right * bottom_left * bottom_right
    return safety_factor


if __name__ == '__main__':
    print(solve())