"""Common solution strategies and patterns for algorithmic problem solving."""

from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass

class ProblemCategory(Enum):
    """Categories of common algorithmic problem types."""
    GRID_TRAVERSAL = "grid_traversal"
    PATHFINDING = "pathfinding"
    SIMULATION = "simulation"
    PATTERN_MATCHING = "pattern_matching"
    STATE_MACHINE = "state_machine"
    OPTIMIZATION = "optimization"
    PARSING = "parsing"
    MATH = "math"
    GRAPH = "graph"
    SEQUENCE = "sequence"
    COMBINATORICS = "combinatorics"
    GEOMETRY = "geometry"
    PERFORMANCE = "performance"
    DYNAMIC_PROGRAMMING = "dynamic_programming"
    BIT_MANIPULATION = "bit_manipulation"
    DATA_STRUCTURES = "data_structures"

@dataclass
class Strategy:
    """Represents a solution strategy."""
    name: str
    description: str
    when_to_use: List[str]
    key_techniques: List[str]
    optimization_tips: List[str]
    example_patterns: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to JSON-serializable dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'when_to_use': self.when_to_use,
            'key_techniques': self.key_techniques,
            'optimization_tips': self.optimization_tips,
            'example_patterns': self.example_patterns
        }

# Comprehensive solution strategies for algorithmic problem solving
SOLUTION_STRATEGIES: Dict[ProblemCategory, List[Strategy]] = {
    ProblemCategory.GRID_TRAVERSAL: [
        Strategy(
            name="Grid Navigation",
            description="Handle 2D/3D grid movement and manipulation",
            when_to_use=[
                "Matrix/grid-based problems",
                "Need to track positions and movements",
                "Pattern matching in grids",
                "Connected regions or flooding",
                "Cellular automata"
            ],
            key_techniques=[
                "Direction vectors",
                "Boundary checking",
                "BFS/DFS traversal",
                "Flood fill",
                "State tracking"
            ],
            optimization_tips=[
                "Use sets for visited positions",
                "Cache boundary calculations",
                "Use array slicing for bulk operations",
                "Consider using numpy for large grids"
            ],
            example_patterns=[
                "directions = [(0,1), (1,0), (0,-1), (-1,0)]",
                "grid[row][col] = new_value",
                "if 0 <= x < width and 0 <= y < height:"
            ]
        )
    ],
    ProblemCategory.PATHFINDING: [
        Strategy(
            name="Graph Traversal",
            description="Find and optimize paths in graphs",
            when_to_use=[
                "Shortest/longest path problems",
                "Graph traversal",
                "Maze navigation",
                "Network routing",
                "State space exploration"
            ],
            key_techniques=[
                "BFS for unweighted paths",
                "Dijkstra's for weighted paths",
                "A* for heuristic search",
                "Floyd-Warshall for all pairs",
                "Topological sort for DAGs",
                "Bidirectional search"
            ],
            optimization_tips=[
                "Use priority queue for weighted paths",
                "Early termination conditions",
                "Bidirectional search for faster results",
                "Cache visited states",
                "Prune impossible paths early"
            ],
            example_patterns=[
                "queue = deque([(start, 0)])",
                "heapq.heappush(pq, (cost, node))",
                "visited = set()",
                "parent = {start: None}"
            ]
        )
    ],
    ProblemCategory.PATTERN_MATCHING: [
        Strategy(
            name="String Pattern Matching",
            description="Find and manipulate patterns in text or sequences",
            when_to_use=[
                "Need to find specific patterns",
                "Text processing required",
                "Regular expressions might help",
                "Sequence matching needed"
            ],
            key_techniques=[
                "Regular expressions",
                "String slicing",
                "Character counting",
                "State tracking",
                "Pattern recognition"
            ],
            optimization_tips=[
                "Use regex for complex patterns",
                "Consider using string methods like split()",
                "Build lookup tables for patterns",
                "Cache intermediate results"
            ],
            example_patterns=[
                "pattern = re.compile(r'\\d+')",
                "text.split('delimiter')",
                "Counter(sequence)"
            ]
        ),
        Strategy(
            name="Sequence Analysis",
            description="Analyze and process sequences of data",
            when_to_use=[
                "Need to find patterns in sequences",
                "Data comes in ordered lists",
                "Need to track changes or trends",
                "Looking for repetition"
            ],
            key_techniques=[
                "Sliding window",
                "Two pointers",
                "State machines",
                "Pattern recognition"
            ],
            optimization_tips=[
                "Use generators for large sequences",
                "Cache repeated calculations",
                "Use built-in functions like map()",
                "Consider using numpy for numerical sequences"
            ],
            example_patterns=[
                "for i in range(len(seq)-1):",
                "left, right = 0, len(seq)-1",
                "window = deque(maxlen=k)"
            ]
        )
    ],
    ProblemCategory.DYNAMIC_PROGRAMMING: [
        Strategy(
            name="State-Based Solutions",
            description="Solve problems by breaking them into overlapping subproblems",
            when_to_use=[
                "Optimization problems",
                "Counting problems",
                "Problems with overlapping subproblems",
                "When greedy approach fails",
                "Pattern matching with wildcards"
            ],
            key_techniques=[
                "State representation",
                "Transition functions",
                "Memoization",
                "Bottom-up tabulation",
                "State compression",
                "Rolling arrays"
            ],
            optimization_tips=[
                "Use minimal state representation",
                "Consider space-time tradeoffs",
                "Clear unnecessary states",
                "Use rolling arrays for space optimization",
                "Identify and cache common subproblems"
            ],
            example_patterns=[
                "@functools.lru_cache(maxsize=None)",
                "dp = [[0] * n for _ in range(m)]",
                "current, previous = [0] * n, [0] * n",
                "state = (pos, mask, count)"
            ]
        )
    ],
    ProblemCategory.BIT_MANIPULATION: [
        Strategy(
            name="Bitwise Operations",
            description="Use bit-level operations for optimization",
            when_to_use=[
                "Set operations",
                "State compression needed",
                "Power of 2 calculations",
                "Flag/state tracking",
                "Memory optimization critical"
            ],
            key_techniques=[
                "Bit masks",
                "Power of 2 operations",
                "Bit counting",
                "State encoding",
                "Bit shifts"
            ],
            optimization_tips=[
                "Use built-in bit operations",
                "Pre-compute bit masks",
                "Use bit states instead of arrays",
                "Consider bit-parallel algorithms",
                "Cache common bit patterns"
            ],
            example_patterns=[
                "state = 1 << n",
                "count = bin(n).count('1')",
                "mask = (1 << n) - 1",
                "next_state = state | (1 << pos)"
            ]
        )
    ],
    ProblemCategory.DATA_STRUCTURES: [
        Strategy(
            name="Specialized Data Structures",
            description="Choose optimal data structures for specific operations",
            when_to_use=[
                "Complex data relationships",
                "Specific operation patterns",
                "Performance critical sections",
                "Memory constraints",
                "Need for ordered data"
            ],
            key_techniques=[
                "Custom hash tables",
                "Tree structures",
                "Priority queues",
                "Union-find",
                "Segment trees",
                "Trie structures"
            ],
            optimization_tips=[
                "Choose based on operation frequency",
                "Consider space-time tradeoffs",
                "Use built-in structures when possible",
                "Implement only needed operations",
                "Balance flexibility and performance"
            ],
            example_patterns=[
                "heapq.heappush(pq, item)",
                "trie = {'children': {}, 'is_end': False}",
                "parent = list(range(n))  # Union-find",
                "segment_tree = [0] * (4 * n)"
            ]
        )
    ],
    ProblemCategory.MATH: [
        Strategy(
            name="Mathematical Operations",
            description="Handle mathematical calculations and formulas",
            when_to_use=[
                "Need to perform calculations",
                "Mathematical patterns involved",
                "Number theory problems",
                "Geometric calculations"
            ],
            key_techniques=[
                "Basic arithmetic",
                "Number theory",
                "Modular arithmetic",
                "Mathematical formulas"
            ],
            optimization_tips=[
                "Use math module functions",
                "Cache expensive calculations",
                "Consider numerical stability",
                "Use appropriate data types"
            ],
            example_patterns=[
                "math.gcd(a, b)",
                "sum(numbers)",
                "x % modulus"
            ]
        )
    ],
    ProblemCategory.SIMULATION: [
        Strategy(
            name="State Evolution",
            description="Simulate system changes over time or steps",
            when_to_use=[
                "Process simulation required",
                "State changes over time",
                "Rule-based systems",
                "Physical simulations",
                "Game mechanics"
            ],
            key_techniques=[
                "State representation",
                "Transition rules",
                "Event scheduling",
                "State caching",
                "Cycle detection"
            ],
            optimization_tips=[
                "Minimize state copying",
                "Cache intermediate states",
                "Detect cycles early",
                "Use efficient state representation",
                "Consider parallel simulation"
            ],
            example_patterns=[
                "next_state = simulate_step(current_state)",
                "seen_states = set()",
                "while not is_final_state(state):",
                "if state in seen: return cycle_length"
            ]
        )
    ],
    ProblemCategory.PARSING: [
        Strategy(
            name="Input Structure Analysis",
            description="Systematically analyze and validate input format before parsing",
            when_to_use=[
                "Input format needs to be determined from examples",
                "Multiple values per line need parsing",
                "Data needs to be grouped or paired",
                "Order of values is significant",
                "Values need sorting or ranking"
            ],
            key_techniques=[
                "Identify exact delimiters (spaces, commas, etc.)",
                "Handle values individually vs. in pairs/groups",
                "Determine if original order matters",
                "Check if sorting is needed",
                "Validate expected number of values"
            ],
            optimization_tips=[
                "Parse and store values in their final required form",
                "Sort only when needed",
                "Use appropriate data structures for required operations",
                "Handle edge cases (empty lines, missing values)",
                "Validate input matches example format"
            ],
            example_patterns=[
                "left, right = line.split(delimiter)",
                "values = [parse_value(v) for v in line.split()]",
                "sorted_values = sorted(values)",
                "pairs = list(zip(left_list, right_list))",
                "validate_format(line, expected_parts=2)"
            ]
        ),
        Strategy(
            name="Robust Input Parsing",
            description="Handle various edge cases and potential input variations",
            when_to_use=[
                "Input may contain empty lines",
                "Whitespace variations possible",
                "Need to handle malformed input",
                "Multiple input formats possible",
                "Data cleaning required"
            ],
            key_techniques=[
                "Strip whitespace consistently",
                "Type conversion with validation",
                "Error handling for malformed input",
                "Line-by-line processing",
                "Format validation checks"
            ],
            optimization_tips=[
                "Use string methods over regex for simple cases",
                "Validate data types early",
                "Keep original data for debugging",
                "Log parsing errors clearly",
                "Build parsing pipeline incrementally"
            ],
            example_patterns=[
                "Leading/trailing whitespace",
                "Empty or comment lines",
                "Mixed number formats",
                "Escaped characters",
                "Multi-line records"
            ]
        ),
        Strategy(
            name="Input-Output Correlation",
            description="Analyze relationship between input structure and expected output",
            when_to_use=[
                "Example input/output pairs provided",
                "Output structure differs from input",
                "Input requires reordering/grouping",
                "When transformation rules are implicit",
                "Multiple valid interpretations possible"
            ],
            key_techniques=[
                "Map example input to output steps",
                "Identify transformation rules",
                "Validate interpretation with examples",
                "Document assumptions explicitly",
                "Test edge cases in examples"
            ],
            optimization_tips=[
                "Draw data flow diagrams",
                "Test interpretation on minimal example",
                "Log intermediate transformations",
                "Verify each transformation step",
                "Compare final structure with example"
            ],
            example_patterns=[
                "Sorting/reordering requirements",
                "Grouping/aggregation needs",
                "Multi-step transformations",
                "State-dependent processing",
                "Implicit rules in examples"
            ]
        ),
        Strategy(
            name="Data Transformation Patterns",
            description="Identify and implement common data transformation patterns",
            when_to_use=[
                "Data needs restructuring",
                "Multiple processing stages",
                "Complex transformations needed",
                "When maintaining data integrity",
                "Processing order matters"
            ],
            key_techniques=[
                "Pipeline processing",
                "Staged transformations",
                "Data structure conversion",
                "State tracking",
                "Validation checkpoints"
            ],
            optimization_tips=[
                "Separate parsing from processing",
                "Use intermediate representations",
                "Validate at transformation boundaries",
                "Keep transformation steps atomic",
                "Document transformation chain"
            ],
            example_patterns=[
                "List/matrix conversions",
                "Sorting with dependencies",
                "State machine transitions",
                "Accumulator patterns",
                "Filter-map-reduce chains"
            ]
        )
    ],
    ProblemCategory.PERFORMANCE: [
        Strategy(
            name="Memory Optimization",
            description="Optimize memory usage and allocation patterns",
            when_to_use=[
                "Large input sizes",
                "Memory constraints",
                "Complex data structures",
                "String processing",
                "Grid/Matrix operations"
            ],
            key_techniques=[
                "Pre-allocation",
                "Primitive types over objects",
                "Efficient data structures",
                "String handling optimization",
                "Sparse matrix representation"
            ],
            optimization_tips=[
                "Pre-allocate arrays when size is known",
                "Use primitive types when possible",
                "Choose appropriate data structures",
                "Use string functions over regex",
                "Consider sparse representations"
            ],
            example_patterns=[
                "grid = [[0] * width for _ in range(height)]",
                "visited = set()  # O(1) lookup",
                "queue = collections.deque()",
                "str.find() instead of re.search()",
                "{(i,j): val} for sparse matrix"
            ]
        ),
        Strategy(
            name="Computational Optimization",
            description="Optimize computation time and algorithm efficiency",
            when_to_use=[
                "Time-critical operations",
                "Complex calculations",
                "Repeated operations",
                "Large search spaces",
                "Pattern matching"
            ],
            key_techniques=[
                "Early termination",
                "Pre-calculation",
                "Caching/Memoization",
                "Search space pruning",
                "Bit manipulation"
            ],
            optimization_tips=[
                "Add early exit conditions",
                "Pre-calculate frequent values",
                "Cache expensive computations",
                "Prune search space early",
                "Use bit operations for sets"
            ],
            example_patterns=[
                "@functools.lru_cache(maxsize=None)",
                "if condition: return early",
                "seen = set() for O(1) lookup",
                "mask = 1 << n  # bit manipulation",
                "precomputed = [calc(i) for i in range(n)]"
            ]
        )
    ],
    ProblemCategory.SEQUENCE: [
        Strategy(
            name="Sequence Processing",
            description="Process, transform, and compare sequences of values",
            when_to_use=[
                "Need to pair values from different lists",
                "Values need sorting before comparison",
                "Need to calculate differences between pairs",
                "Order matters for matching values",
                "Need to align or correspond elements"
            ],
            key_techniques=[
                "Sort lists independently",
                "Pair corresponding elements",
                "Calculate differences or distances",
                "Handle lists of equal/unequal length",
                "Track original vs sorted positions"
            ],
            optimization_tips=[
                "Sort once at the start",
                "Use zip() for pairing elements",
                "Pre-calculate values when possible",
                "Handle edge cases (empty lists, single element)",
                "Validate list lengths match"
            ],
            example_patterns=[
                "sorted_left = sorted(left_values)",
                "for x, y in zip(sorted_left, sorted_right)",
                "differences = [abs(a - b) for a, b in pairs]",
                "if len(left) != len(right): handle_error()",
                "total = sum(abs(x - y) for x, y in pairs)"
            ]
        )
    ],
    ProblemCategory.COMBINATORICS: [
        Strategy(
            name="Combinatorial Calculations",
            description="Calculate combinations, permutations, and arrangements",
            when_to_use=[
                "Counting problems",
                "Arrangement problems",
                "Selection problems",
                "Need to generate all combinations",
                "Need to calculate permutations"
            ],
            key_techniques=[
                "Factorial calculations",
                "Combination formulas",
                "Permutation formulas",
                "Recursion",
                "Dynamic programming"
            ],
            optimization_tips=[
                "Use math.comb() for combinations",
                "Use math.perm() for permutations",
                "Cache intermediate results",
                "Use dynamic programming for large inputs",
                "Consider using itertools"
            ],
            example_patterns=[
                "math.comb(n, k)",
                "math.perm(n, k)",
                "cache = {}",
                "dp = [[0] * n for _ in range(k)]",
                "import itertools"
            ]
        )
    ],
    ProblemCategory.GEOMETRY: [
        Strategy(
            name="Geometric Calculations",
            description="Calculate distances, areas, and volumes",
            when_to_use=[
                "Need to calculate distances",
                "Need to calculate areas",
                "Need to calculate volumes",
                "Need to calculate angles",
                "Need to calculate shapes"
            ],
            key_techniques=[
                "Distance formulas",
                "Area formulas",
                "Volume formulas",
                "Angle calculations",
                "Shape recognition"
            ],
            optimization_tips=[
                "Use math.hypot() for distances",
                "Use math.pi for area/volume calculations",
                "Cache intermediate results",
                "Consider using numpy for vector calculations",
                "Use geometric libraries when possible"
            ],
            example_patterns=[
                "math.hypot(x, y)",
                "math.pi * r ** 2",
                "4/3 * math.pi * r ** 3",
                "math.atan2(y, x)",
                "import numpy as np"
            ]
        )
    ],
    ProblemCategory.PERFORMANCE: [
        Strategy(
            name="Memory Optimization",
            description="Optimize memory usage and allocation patterns",
            when_to_use=[
                "Large input sizes",
                "Memory constraints",
                "Complex data structures",
                "String processing",
                "Grid/Matrix operations"
            ],
            key_techniques=[
                "Pre-allocation",
                "Primitive types over objects",
                "Efficient data structures",
                "String handling optimization",
                "Sparse matrix representation"
            ],
            optimization_tips=[
                "Pre-allocate arrays when size is known",
                "Use primitive types when possible",
                "Choose appropriate data structures",
                "Use string functions over regex",
                "Consider sparse representations"
            ],
            example_patterns=[
                "grid = [[0] * width for _ in range(height)]",
                "visited = set()  # O(1) lookup",
                "queue = collections.deque()",
                "str.find() instead of re.search()",
                "{(i,j): val} for sparse matrix"
            ]
        ),
        Strategy(
            name="Computational Optimization",
            description="Optimize computation time and algorithm efficiency",
            when_to_use=[
                "Time-critical operations",
                "Complex calculations",
                "Repeated operations",
                "Large search spaces",
                "Pattern matching"
            ],
            key_techniques=[
                "Early termination",
                "Pre-calculation",
                "Caching/Memoization",
                "Search space pruning",
                "Bit manipulation"
            ],
            optimization_tips=[
                "Add early exit conditions",
                "Pre-calculate frequent values",
                "Cache expensive computations",
                "Prune search space early",
                "Use bit operations for sets"
            ],
            example_patterns=[
                "@functools.lru_cache(maxsize=None)",
                "if condition: return early",
                "seen = set() for O(1) lookup",
                "mask = 1 << n  # bit manipulation",
                "precomputed = [calc(i) for i in range(n)]"
            ]
        )
    ]
}

# Keywords that suggest different problem categories
CATEGORY_KEYWORDS = {
    ProblemCategory.GRID_TRAVERSAL: ['grid', 'matrix', 'map', 'adjacent', '2d'],
    ProblemCategory.PATHFINDING: ['path', 'route', 'distance', 'shortest', 'steps'],
    ProblemCategory.SIMULATION: ['simulate', 'process', 'steps', 'change', 'time'],
    ProblemCategory.PATTERN_MATCHING: ['match', 'find', 'pattern', 'repeat', 'sequence'],
    ProblemCategory.STATE_MACHINE: [
        'transition_rules', 'state_change', 'state_machine', 'automaton', 'state_diagram',
        'finite_states', 'state_transitions', 'current_state', 'next_state', 'valid_transitions'
    ],
    ProblemCategory.OPTIMIZATION: [
        'minimize', 'maximize', 'optimal', 'best', 'efficient',
        'least_cost', 'most_efficient', 'optimize_for', 'minimum_cost', 'maximum_value',
        'best_possible', 'fewest_steps', 'lowest_cost', 'highest_score'
    ],
    ProblemCategory.PARSING: [
        # Basic parsing keywords
        'input', 'parse', 'format', 'read', 'line',
        # Structure analysis keywords
        'structure', 'pattern', 'delimiter', 'separated', 'split',
        'space-separated', 'line-by-line', 'tab-separated', 'comma-separated',
        # Transformation keywords
        'convert', 'transform', 'arrange', 'order', 'sort',
        # Validation keywords
        'validate', 'verify', 'check', 'ensure', 'match',
        # Example-related keywords
        'example', 'shown', 'following', 'like', 'format',
        # Data organization keywords
        'pair', 'group', 'list', 'sequence', 'series',
        'columns', 'rows', 'fields', 'values', 'entries'
    ],
    ProblemCategory.MATH: ['calculate', 'number', 'formula', 'sequence', 'count'],
    ProblemCategory.GRAPH: ['connect', 'node', 'edge', 'network', 'path'],
    ProblemCategory.SEQUENCE: [
        # Ordering and comparison
        'series', 'order', 'next', 'previous', 'pattern',
        'smallest', 'largest', 'ascending', 'descending', 'sorted',
        'minimum', 'maximum', 'increasing', 'decreasing', 'rank',
        'first', 'last', 'nth', 'position', 'index',
        # Pairing and matching
        'pair_up', 'match_up', 'corresponding', 'align', 'compare',
        'difference_between', 'distance_between', 'gap', 'spacing'
    ],
    ProblemCategory.COMBINATORICS: ['combine', 'arrange', 'possible', 'ways', 'permutation'],
    ProblemCategory.GEOMETRY: ['area', 'distance', 'point', 'line', 'shape'],
    ProblemCategory.PERFORMANCE: ['optimize', 'fast', 'efficient', 'improve', 'speed'],
    ProblemCategory.DYNAMIC_PROGRAMMING: ['optimal', 'minimum', 'maximum', 'count', 'ways'],
    ProblemCategory.BIT_MANIPULATION: ['bit', 'binary', 'mask', 'power', 'state'],
    ProblemCategory.DATA_STRUCTURES: ['store', 'retrieve', 'order', 'structure', 'collection']
}

def get_strategies_for_problem(problem_text: str) -> List[str]:
    """Analyze problem text and return relevant strategy names.
    
    Args:
        problem_text: The problem description
        
    Returns:
        List of potentially applicable strategy names
    """
    strategies = []
    
    # Find relevant categories based on keywords
    problem_text = problem_text.lower()
    category_scores = {}
    
    # Score each category based on keyword matches
    for category, words in CATEGORY_KEYWORDS.items():
        score = sum(problem_text.count(word) for word in words)
        if score > 0:
            category_scores[category] = score
            
    # If no categories match, default to PATTERN_MATCHING and MATH
    if not category_scores:
        matching_categories = [ProblemCategory.PATTERN_MATCHING, ProblemCategory.MATH]
    else:
        # Get the top 2 scoring categories
        matching_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:2]
        matching_categories = [cat for cat, _ in matching_categories]
            
    # Get strategies for each matching category
    for category in matching_categories:
        strategies.extend(strategy.name for strategy in SOLUTION_STRATEGIES[category])
    
    return strategies

def create_strategy_prompt(strategies: List[Strategy]) -> str:
    """Create a prompt section for solution strategies.
    
    Args:
        strategies: List of relevant strategies
        
    Returns:
        Prompt text guiding solution approach
    """
    prompt = "\nRecommended Solution Strategies:\n"
    
    for strategy in strategies:
        prompt += f"\n{strategy.name}:\n"
        prompt += f"Description: {strategy.description}\n"
        prompt += f"When to use: {', '.join(strategy.when_to_use)}\n"
        prompt += f"Key techniques: {', '.join(strategy.key_techniques)}\n"
        prompt += f"Optimization tips: {', '.join(strategy.optimization_tips)}\n"
        prompt += "\nExample patterns:\n"
        for pattern in strategy.example_patterns:
            prompt += f"  {pattern}\n"
        
    return prompt
