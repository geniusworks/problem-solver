import sys
from typing import List, Tuple, Set

def solve() -> int:
    """
    Read red tile coordinates from input.txt and find the largest rectangle area
    using two red tiles as opposite corners, where all tiles in the rectangle
    are either red or green (inside or on the polygon boundary).
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(0)
        return 0

    points: List[Tuple[int, int]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) != 2:
            continue
        try:
            x = int(parts[0].strip())
            y = int(parts[1].strip())
            points.append((x, y))
        except ValueError:
            continue

    n = len(points)
    if n < 2:
        print(0)
        return 0

    # The polygon is the list of red tiles in order
    polygon = points

    # Determine bounding box
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)

    # Create a set of red tiles for quick lookup
    red_tiles = set(points)

    # Build the set of green tiles:
    # 1. Tiles on the segments connecting consecutive red tiles (including endpoints)
    # 2. All tiles inside the polygon (using ray casting)
    # Since the polygon is formed by axis-aligned segments between consecutive red tiles,
    # we can efficiently compute the interior.

    # First, mark all tiles on the boundary (segments between consecutive red tiles)
    # and all tiles inside the polygon.

    # For efficiency, we'll use a different approach:
    # A tile (x, y) is valid if it's a red tile or if it's inside the polygon (including boundary).
    # Since the polygon is simple and axis-aligned segments connect consecutive red tiles,
    # we can use the ray-casting algorithm with boundary checking.

    # However, for large inputs, checking every tile in a rectangle is too slow.
    # Instead, we can precompute which tiles are valid within the bounding box.
    # But the bounding box might be large.

    # Alternative approach: For each pair of red tiles, check if the rectangle they form
    # is entirely composed of valid tiles. We can do this by checking if any tile in the
    # rectangle is NOT valid. A tile is invalid if it's outside the polygon.

    # Key insight: Since the polygon is defined by axis-aligned segments between consecutive
    # red tiles, and all interior tiles are green, a rectangle is valid if and only if
    # it doesn't contain any tile that is outside the polygon.

    # For a rectangle to be invalid, there must exist a tile (x, y) in the rectangle that is
    # outside the polygon. We can check this by seeing if the rectangle intersects the
    # exterior of the polygon.

    # A more efficient approach: For each row y in the rectangle, determine the range of x
    # that is inside the polygon. If the rectangle's x-range [x_min, x_max] is not fully
    # contained in the valid x-range for that row, then the rectangle is invalid.

    # Let's precompute for each y, the intervals of x that are inside the polygon.
    # Since the polygon is formed by axis-aligned segments, for each y, the intersection
    # of the polygon with that row is a union of intervals.

    # Actually, since the segments are axis-aligned, the polygon is an orthogonal polygon.
    # For each y, we can find the x-intervals that are inside.

    # Let's compute this efficiently:
    # For each horizontal segment (y1, x1) to (y2, x2) where y1 == y2, this is a horizontal edge.
    # For each vertical segment (y1, x) to (y2, x), this spans y from min(y1,y2) to max(y1,y2) at x.

    # We'll use a sweep line approach or simply for each y in the bounding box, find the valid x intervals.

    # Given the constraints (496 red tiles), the number of segments is 496.
    # The bounding box might be large, but we only need to check y-values that are relevant.

    # Let's take a different, more direct approach:
    # For each pair of red tiles (i, j), form the rectangle. To check if it's valid,
    # we need to verify that no tile in the rectangle is outside the polygon.
    # A tile is outside the polygon if a ray cast from it to the right crosses an odd number of edges.

    # But checking every tile is too slow. Instead, we can check if the rectangle
    # contains any point that is outside. This is equivalent to checking if the
    # rectangle is not a subset of the polygon.

    # For an orthogonal polygon, a rectangle is inside the polygon if and only if:
    # 1. All four corners are inside (or on boundary).
    # 2. No polygon edge crosses the interior of the rectangle.

    # Let's implement this check.

    def point_in_polygon(px: int, py: int, poly: List[Tuple[int, int]]) -> bool:
        """
        Check if a point is inside a polygon using the ray-casting algorithm.
        Returns True if the point is inside or on the boundary.
        """
        inside = False
        j = len(poly) - 1
        for i in range(len(poly)):
            xi, yi = poly[i]
            xj, yj = poly[j]
            # Check if the point is on the edge
            if yi == yj:
                # Horizontal edge
                if py == yi and min(xi, xj) <= px <= max(xi, xj):
                    return True
            elif xi == xj:
                # Vertical edge
                if px == xi and min(yi, yj) <= py <= max(yi, yj):
                    return True
            else:
                # Check if point is on the line segment
                cross = (xj - xi) * (py - yi) - (yj - yi) * (px - xi)
                if cross == 0 and min(xi, xj) <= px <= max(xi, xj) and min(yi, yj) <= py <= max(yi, yj):
                    return True

            # Ray casting
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def segments_intersect_rectangle(x1: int, y1: int, x2: int, y2: int,
                                     rx_min: int, rx_max: int, ry_min: int, ry_max: int) -> bool:
        """
        Check if the line segment from (x1,y1) to (x2,y2) intersects the interior of the
        rectangle [rx_min, rx_max] x [ry_min, ry_max].
        """
        # The segment is axis-aligned (by problem constraints)
        if y1 == y2:
            # Horizontal segment
            if ry_min < y1 < ry_max:
                # Check if x-range overlaps with rectangle interior
                seg_min_x = min(x1, x2)
                seg_max_x = max(x1, x2)
                if seg_min_x < rx_max and seg_max_x > rx_min:
                    # Check if there's a point in the segment that is strictly inside the rectangle
                    # The intersection with the rectangle's x-range
                    inter_min = max(seg_min_x, rx_min)
                    inter_max = min(seg_max_x, rx_max)
                    if inter_min < inter_max:
                        # There's an interior point
                        return True
                    # Check if the segment passes through the interior (not just touching boundary)
                    # If the segment is at y1 which is strictly inside, and x-range overlaps with interior
                    # Actually, if y1 is strictly inside ry_min..ry_max, and the x-range of the segment
                    # overlaps with (rx_min, rx_max), then it intersects the interior.
                    if seg_min_x < rx_max and seg_max_x > rx_min:
                        return True
        elif x1 == x2:
            # Vertical segment
            if rx_min < x1 < rx_max:
                seg_min_y = min(y1, y2)
                seg_max_y = max(y1, y2)
                if seg_min_y < ry_max and seg_max_y > ry_min:
                    return True
        return False

    def rectangle_is_valid(x_min: int, x_max: int, y_min: int, y_max: int) -> bool:
        """
        Check if all tiles in the rectangle are valid (red or green).
        This is true if and only if the rectangle is entirely inside the polygon.
        """
        # Check all four corners
        for cx in [x_min, x_max]:
            for cy in [y_min, y_max]:
                if not point_in_polygon(cx, cy, polygon):
                    return False

        # Check if any polygon edge crosses the interior of the rectangle
        for i in range(len(polygon)):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % len(polygon)]
            if segments_intersect_rectangle(x1, y1, x2, y2, x_min, x_max, y_min, y_max):
                return False

        return True

    max_area = 0

    for i in range(n):
        x1, y1 = points[i]
        for j in range(i + 1, n):
            x2, y2 = points[j]
            x_min = min(x1, x2)
            x_max = max(x1, x2)
            y_min = min(y1, y2)
            y_max = max(y1, y2)

            if rectangle_is_valid(x_min, x_max, y_min, y_max):
                width = x_max - x_min + 1
                height = y_max - y_min + 1
                area = width * height
                if area > max_area:
                    max_area = area

    print(max_area)
    return max_area


if __name__ == '__main__':
    solve()