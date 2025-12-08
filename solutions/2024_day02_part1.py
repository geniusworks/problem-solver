def solve() -> int:
    with open('input.txt') as f:
        lines = [line.strip() for line in f.readlines()]

    def is_safe(report: str) -> bool:
        levels = list(map(int, report.split()))
        increasing = all(levels[i] <= levels[i+1] for i in range(len(levels)-1))
        decreasing = all(levels[i] >= levels[i+1] for i in range(len(levels)-1))

        if increasing or decreasing:
            return all(abs(levels[i] - levels[i+1]) in [1, 2, 3] for i in range(len(levels)-1))
        else:
            return False

    safe_reports = sum(1 for line in lines if is_safe(line))
    return safe_reports

if __name__ == '__main__':
    print(solve())