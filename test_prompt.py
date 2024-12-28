from pathlib import Path
import logging

from shared.parser import parse_problem_text
from shared.problem_analysis import ProblemAnalyzer
from shared.prompts import PromptGenerator

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def main():
    # Read problem
    logger.debug("Reading problem file...")
    with open('years/2021/day01/problem.txt') as f:
        text = f.read()
    
    # Parse and analyze
    logger.debug("Parsing problem text...")
    problem = parse_problem_text(text, 2021, 1)
    
    logger.debug("Creating analyzer...")
    analyzer = ProblemAnalyzer()
    
    logger.debug("Analyzing problem...")
    analyzed_problem = analyzer.analyze_problem(problem)
    
    # Generate prompt
    logger.debug("Creating prompt generator...")
    generator = PromptGenerator(Path('prompts'))
    
    logger.debug("Generating prompt...")
    prompt = generator.generate_prompt(analyzed_problem, 'basic_solution')
    print(prompt)

if __name__ == '__main__':
    main()
