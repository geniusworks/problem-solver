def solve(input_file_path):
    # Read the input file
    with open(input_file_path, "r") as f:
        lines = f.readlines()

    # Parse the input into two lists of integers
    left_list = [int(line) for line in lines[0].split(",")]
    right_list = [int(line) for line in lines[1].split(",")]

    # Find the pairwise distances between the lists
    pairwise_distances = []
    for i in range(len(left_list)):
        for j in range(len(right_list)):
            pairwise_distances.append(abs(left_list[i] - right_list[j]))

    # Sum the pairwise distances to find the total distance
    total_distance = sum(pairwise_distances)

    return total_distance


if __name__ == "__main__":
    print(solve("input.txt"))
