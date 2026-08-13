# Learning System

The learning system helps improve problem-solving performance by tracking strategy effectiveness and solution patterns.

## Components

### Database Schema (`schema.sql`)

The SQLite database tracks:

1. **Strategy Results**
   - Problem attempts and outcomes
   - Execution metrics (time, memory)
   - Success/failure patterns
   - Strategy combinations used

2. **Strategy Weights**
   - Success rates by strategy
   - Resource usage patterns
   - Problem type applicability
   - Usage frequency

3. **Problem Characteristics**
   - Common features
   - Successful approaches
   - Solution metrics
   - Attempt history

## Integration

The learning system is integrated into the main solver through:

1. **Strategy Selection** (`learning/optimizer.py`)
   ```python
   optimizer = StrategyOptimizer(learning_dir, workspace_dir)
   strategies = optimizer.get_recommended_strategies(problem_characteristics)
   ```

2. **Result Recording** (`learning/database.py`)
   ```python
   db = LearningDatabase()  # defaults to the learning/ dir -> learning/solver.db
   db.store_result(
       problem_id="2024_day01_part1",
       strategies=["dynamic_programming"],
       success=True,
       metrics={...}
   )
   ```

3. **Performance Analysis** (`shared/solver.py`)
   - Tracks execution metrics
   - Updates strategy weights
   - Records failure patterns

## Strategy Optimization

The system optimizes strategy selection by:

1. **Problem Analysis**
   - Extracts key characteristics
   - Identifies similar problems
   - Determines complexity factors

2. **Strategy Matching**
   - Matches characteristics to strategies
   - Considers past performance
   - Balances exploration/exploitation

3. **Performance Tracking**
   - Records execution metrics
   - Tracks resource usage
   - Identifies failure patterns

4. **Weight Updates**
   - Updates strategy weights
   - Adjusts for problem types
   - Considers execution costs

## Usage

The learning system is automatically used by the solver, but you can also:

1. **View Strategy Stats**
   ```python
from learning.database import LearningDatabase

db = LearningDatabase()
stats = db.get_strategy_weights()
```

2. **Analyze Patterns**
   ```python
from learning.optimizer import StrategyOptimizer

optimizer = StrategyOptimizer(learning_dir, workspace_dir)
patterns = optimizer.analyze_failures()
```

3. **Reset Learning**
   ```bash
   rm learning/solver.db
   python -c "from learning.database import LearningDatabase; LearningDatabase()"
   ```

## Development

When adding new features:

1. Update schema.sql if adding new metrics
2. Update database.py with new queries
3. Modify learning.py for new optimization logic
4. Test with various problem types

## Notes

- Database file (solver.db) is not tracked in git
- Learning is specific to your local setup
- Strategy weights adapt to your hardware
