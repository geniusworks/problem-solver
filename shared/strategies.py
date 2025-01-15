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
                "Grid state tracking",
                "Flood fill",
                "Connected components",
                "Manhattan distance"
            ],
            optimization_tips=[
                "Use arrays instead of string operations",
                "Pre-calculate grid dimensions",
                "Cache frequently accessed positions",
                "Use sets for visited tracking",
                "Consider sparse matrix for large grids"
            ],
            example_patterns=[
                "directions = [(0,1), (1,0), (0,-1), (-1,0)]",
                "grid = [list(row) for row in input_data]",
                "visited = set()",
                "def in_bounds(x, y): return 0 <= x < width and 0 <= y < height"
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
            name="Mathematical Solutions",
            description="Leverage mathematical properties and algorithms",
            when_to_use=[
                "Number theory problems",
                "Geometric calculations",
                "Pattern recognition",
                "Optimization problems",
                "Sequence analysis"
            ],
            key_techniques=[
                "GCD/LCM calculations",
                "Prime factorization",
                "Modular arithmetic",
                "Matrix operations",
                "Geometric algorithms",
                "Combinatorics"
            ],
            optimization_tips=[
                "Use mathematical shortcuts",
                "Consider modular arithmetic",
                "Pre-compute common values",
                "Use bit operations for math",
                "Cache calculated results"
            ],
            example_patterns=[
                "math.gcd(a, b)",
                "pow(base, exp, mod)",
                "combinations = math.comb(n, r)",
                "matrix_multiply(a, b)"
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

def get_strategies_for_problem(problem_text: str) -> List[str]:
    """Analyze problem text and return relevant strategy names.
    
    Args:
        problem_text: The problem description
        
    Returns:
        List of potentially applicable strategy names
    """
    strategies = []
    
    # Keywords indicating problem types
    keywords = {
        ProblemCategory.GRID_TRAVERSAL: ['grid', 'matrix', 'map', '2d', 'adjacent'],
        ProblemCategory.PATHFINDING: ['path', 'route', 'shortest', 'graph', 'maze'],
        ProblemCategory.SIMULATION: ['simulate', 'step', 'change', 'evolve', 'rule'],
        ProblemCategory.PATTERN_MATCHING: ['pattern', 'match', 'find', 'string', 'text'],
        ProblemCategory.MATH: ['calculate', 'number', 'formula', 'sequence', 'count'],
        ProblemCategory.DYNAMIC_PROGRAMMING: ['optimal', 'minimum', 'maximum', 'count', 'ways'],
        ProblemCategory.BIT_MANIPULATION: ['bit', 'binary', 'mask', 'power', 'state'],
        ProblemCategory.DATA_STRUCTURES: ['store', 'retrieve', 'order', 'structure', 'collection']
    }
    
    # Find relevant categories based on keywords
    problem_text = problem_text.lower()
    for category, words in keywords.items():
        if any(word in problem_text for word in words):
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
