def solve(input_file_path):
    with open(input_file_path) as f:
        measurements = [int(line.strip()) for line in f]
    prev = measurements[0]
    count = 0
    for curr in measurements[1:]:
        if curr > prev:
            count += 1
        prev = curr
    return count


if __name__ == "__main__":
    print(solve("input.txt"))
