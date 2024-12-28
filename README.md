# Advent of Code Solver

An automated solver for [Advent of Code](https://adventofcode.com) problems.

## Author

Martin Diekhoff  
 2024  
GitHub: [github.com/geniusworks](https://github.com/geniusworks)

## About

The objective of this project is to create an automated [Advent of Code](https://adventofcode.com) solver.

Initially we will solve the [Day 1](https://adventofcode.com/2021/day/1) problem.

Eventually we will solve all of the problems for all years.

## Methodology

The solver will CONSIDER using the following:

`
The solver will read the input from the `input.txt` file and will output the result to the `output.txt` file.
The solver will use the [Python](https://www.python.org/) programming language.
The solver will use the [Pandas](https://pandas.pydata.org/) library.
The solver will use the [NumPy](https://numpy.org/) library.
The solver will use the [Matplotlib](https://matplotlib.org/) library.
The solver will use the [Scikit-Learn](https://scikit-learn.org/stable/) library.
The solver will use the [requests](https://requests.readthedocs.io/en/latest/) library.
The solver will use the [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) library.
The solver will use the [PyYAML](https://pyyaml.org/wiki/PyYAML) library.
The solver will use the [Jinja2](https://jinja.palletsprojects.com/) library.
The solver will use the [Click](https://click.palletsprojects.com/) library.
The solver will use the [PyTest](https://docs.pytest.org/en/latest/) library.
The solver will use the [Black](https://black.readthedocs.io/en/latest/) library.
The solver will use the [isort](https://pycqa.github.io/isort/) library.
The solver will use the [Flake8](https://flake8.pycqa.org/en/latest/) library.
The solver will use the [PyLint](https://pylint.pycqa.org/en/latest/) library.
The solver will use the [MyPy](https://mypy.readthedocs.io/en/stable/) library.
The solver will use the [Sphinx](https://www.sphinx-doc.org/en/master/) library.
The solver will use the [Git](https://git-scm.com/) library.
The solver will use the [GitHub](https://github.com/) library.
The solver will use the [PyPI](https://pypi.org/) library.
The solver will use the [Google Colab](https://colab.research.google.com/) library.
The solver will use the [Jupyter](https://jupyter.org/) library.
The solver will use the [Docker](https://www.docker.com/) library.
The solver will use the [Kubernetes](https://kubernetes.io/) library.
`

The solver will create directories as needed according to the following pattern:

`
AdventOfCode/
│
├── years/
│   ├── 2023/
│   │   ├── day01/
│   │   │   ├── input.txt        # Problem input data
│   │   │   ├── example.txt      # Example data from problem description
│   │   │   ├── problem.txt      # Full problem description text
│   │   │   ├── logic.txt        # Problem broken down into logical components
│   │   │   ├── attempts.log     # Log of solution attempts and their results
│   │   │   ├── part1.py
│   │   │   ├── part2.py
│   │   │   └── README.md
│   │   ├── day02/
│   │   │   ├── input.txt
│   │   │   ├── example.txt
│   │   │   ├── problem.txt
│   │   │   ├── logic.txt
│   │   │   ├── attempts.log
│   │   │   ├── part1.py
│   │   │   ├── part2.py
│   │   │   └── README.md
│   │   └── ...
│   ├── 2022/
│   │   ├── day01/
│   │   │   ├── input.txt
│   │   │   ├── example.txt
│   │   │   ├── problem.txt
│   │   │   ├── logic.txt
│   │   │   ├── attempts.log
│   │   │   ├── part1.py
│   │   │   ├── part2.py
│   │   │   └── README.md
│   │   └── ...
│   └── ...
│
├── shared/
│   ├── utils.py
│   └── config.py
│
├── README.md
└── .gitignore
`

## Additional Methodology

1. Problem Text Storage
   - The full problem text will be stored in `problem.txt` to avoid repeated URL requests
   - Example data from the problem will be stored in `example.txt`
   - The problem's logical components will be analyzed and stored in `logic.txt`

2. Input Data Management
   - Problem input data will be downloaded once and stored in `input.txt`
   - The solver will check for existing input data before making new requests

3. Solution Attempt Logging
   - All solution attempts will be logged in `attempts.log`
   - Each log entry will include:
     - Timestamp
     - Part number (1 or 2)
     - Attempted solution
     - Result (accepted/rejected)
     - Any feedback received

4. Solution Submission
   - Solutions will only be submitted after:
     - Passing all example test cases
     - Code review and optimization
     - Proper logging of the attempt

## Development Process

1. Setup Phase
   - Initialize problem directory and files
   - Retrieve and store problem text
   - Extract example data
   - Analyze problem requirements
   - Download input data

2. Solution Development
   - Create test cases from example data
   - Implement solution with proper error handling
   - Test solution against examples
   - Log all solution attempts
   - Submit only after passing all tests

3. Documentation
   - Maintain CHECKPOINT.md for development progress
   - Document each problem's solution approach
   - Track attempted solutions and their results
   - Record any insights or lessons learned

4. Code Quality
   - Follow Python best practices
   - Use type hints
   - Include error handling
   - Add logging for debugging
   - Rate limit API requests

## Getting Started

1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.template` to `.env` and add your AOC session cookie
6. Run setup for a problem: `python years/YYYY/dayDD/setup.py`
7. Implement solution in `part1.py` and `part2.py`
8. Check CHECKPOINT.md for current status and next steps

<!-- Instructions to AI:
- We will build this solver using any recommended stable public libraries, but also custom libraries as needed.
- First we will work on the initially proposed problem (2021 Day 1), then we will work on all of the problems for all years.
- Let's confirm a fully automated working solution from start to finish first, initiated by a command line prompt.
- The command prompt will accept a year and day number, or default to the current year and day number if we are within contest range.
- Note that contest range is every year from Day 1 (starts December 1 at 00:00:00 EST) up to Day 25 (starts December 25 at 00:00:00 EST).
-->

<!-- Instructions to AI:
- Check to see if we've done any of these things already, but if not proceed as best you can and ask for guidance as needed:
- 1. Make sure the necessary directories and files exist.
- 2. Make sure the necessary libraries are installed.
- 3. Retrieve the problem text from the target URI (use existing or create a service to retrieve and parse the problem text).
- 4. Create a prompt to systematically interpret the problem text and parse it into logical parts (save this in a logic.txt file).
-->

<!-- Instructions to AI:
- We will refine these instructions after we have accomplished a few basic things first.
- One of those things will be for you to define a test procedure to determine whether we have succeeded so far.
-->

<!-- Instructions to AI:
- Note that anytime you make useful progress, you should record that in a CHECKPOINT.md file (placed where it is most logical).
- What you record in CHECKPOINT.md should be sufficient for you to continue where you left off in a new session.
-->
