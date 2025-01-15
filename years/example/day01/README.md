# Example Problem Structure

This directory shows the expected structure for an Advent of Code problem solution:

```
day01/
├── README.md           # This file
├── problem.txt         # Problem description (not included - download from AoC)
├── problem.html        # Cached HTML (not included - downloaded when needed)
├── problem_meta.json   # Problem state and progress
├── input.txt          # Problem input (not included - unique per user)
├── examples/          # Example test cases from problem
│   ├── example_1.json
│   └── metadata.json
└── attempts/          # Solution attempts
    └── attempt_*.json
```

Note: This is just an example structure. When you run the problem solver, it will:
1. Create these directories
2. Download problem text and input from AoC using your session
3. Extract examples from the problem text
4. Track your solution attempts

Please do not commit your personal AoC data, as:
1. Puzzle inputs should not be shared (as requested by AoC creator)
2. Solutions are more rewarding when discovered yourself
3. Cached pages contain your session cookie
