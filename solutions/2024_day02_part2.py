def solve():
    # Read input from file
    with open('input.txt', 'r') as f:
        lines = [line.strip() for line in f.readlines()]

    # Function to check if report is safe
    def is_safe(report):
        levels = list(map(int, report.split()))
        max_level = max(levels)
        return all(level <= 9 for level in levels) or any(all(l <= 9 for l in levels[:-i]) and levels[-i] > 9 for i in range(1, len(levels)))

    # Function to count safe reports with the Problem Dampener
    def count_safe_dampened(reports):
        count = 0
        for report in reports:
            if is_safe(report):
                count += 1
            else:
                levels = list(map(int, report.split()))
                for i in range(len(levels)):
                    new_report = ' '.join(str(level) for j, level in enumerate(levels) if j != i)
                    if is_safe(new_report):
                        count += 1
                        break
        return count

    # Count total safe reports with the Problem Dampener
    safe_count = count_safe_dampened(lines)

    # Print result
    print(safe_count)


if __name__ == "__main__":
    solve()