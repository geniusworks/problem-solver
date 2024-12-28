# Advent of Code Solver

An automated solver for Advent of Code challenges.

## Setup

1. Clone this repository
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.template` to `.env` and add your Advent of Code session cookie

## Project Structure

```
advent-of-code-solver/
├── shared/             # Shared utilities and configuration
│   ├── utils.py       # Common utilities (HTTP requests, file handling)
│   └── config.py      # Configuration and constants
├── years/             # Solutions organized by year
│   └── 2021/         # Year-specific solutions
│       └── day01/    # Day-specific solutions
│           ├── setup.py    # Sets up problem files
│           ├── part1.py    # Solution for part 1
│           ├── part2.py    # Solution for part 2
│           ├── problem.txt # Problem description
│           ├── example.txt # Example input
│           └── input.txt   # Your puzzle input (gitignored)
└── requirements.txt    # Python dependencies
```

## Usage

1. Set up your session cookie in `.env` (see Configuration below)
2. Navigate to a specific day's directory
3. Run `setup.py` to fetch the problem and input
4. Solve the problem in `part1.py` and `part2.py`

## Configuration

Create a `.env` file with your Advent of Code session cookie:
```
AOC_SESSION=your_session_cookie_here
```

To get your session cookie:
1. Log in to [Advent of Code](https://adventofcode.com)
2. Open browser developer tools (F12)
3. Go to Application/Storage > Cookies
4. Copy the value of the 'session' cookie

## Features

- Automatic problem and input fetching
- Session cookie management via `.env`
- Browser-like request headers to avoid rate limiting
- Organized project structure by year and day
- Example extraction from problem description
- Proper error handling and logging

## Development Notes

- Input files are gitignored for privacy
- Browser-like headers are used for API requests
- HTML parsing uses Python's built-in `html.parser`
- All file operations use pathlib for cross-platform compatibility

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
