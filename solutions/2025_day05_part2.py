def solve() -> int:
    """
    Reads ingredient ID ranges from input.txt and calculates the total number
    of unique IDs covered by these ranges.
    
    Returns:
        int: The total count of unique fresh ingredient IDs.
    """
    try:
        with open('input.txt', 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return 0

    ranges = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split('-')
        if len(parts) != 2:
            continue
        try:
            start = int(parts[0])
            end = int(parts[1])
            ranges.append((start, end))
        except ValueError:
            continue

    if not ranges:
        return 0

    # Sort ranges by start value, then by end value
    ranges.sort(key=lambda x: (x[0], x[1]))

    total_count = 0
    current_start, current_end = ranges[0]

    for i in range(1, len(ranges)):
        next_start, next_end = ranges[i]
        
        # If the next range overlaps with the current merged range
        if next_start <= current_end:
            # Merge them by extending the end if necessary
            current_end = max(current_end, next_end)
        else:
            # No overlap: add the length of the current interval
            total_count += (current_end - current_start + 1)
            # Start a new interval
            current_start, current_end = next_start, next_end

    # Add the last interval
    total_count += (current_end - current_start + 1)

    return total_count

if __name__ == '__main__':
    print(solve())