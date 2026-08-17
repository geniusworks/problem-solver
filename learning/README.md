# Learning System

The learning system helps improve problem-solving performance by tracking strategy effectiveness and solution patterns.

> **Honest status (2026-08-15):** of the tables below, only **`model_performance`** has ever held
> measured data — it records each model's oracle-verified outcomes and feeds `_get_top_models`
> ranking (with a cold-start fallback to the installed models when empty). The **strategy** tables
> (`strategy_results`, `strategy_weights`, `problem_characteristics`, `improvement_history`) have
> never been populated by a real run: strategy *seeding* works (`shared/strategy_recommender.py`),
> but effectiveness *learning* is scaffolding whose write path isn't exercised by the solve loop.
> Sections below describing weight updates and adaptation describe the intended design, not current
> behaviour. Re-wire only with harness evidence, per `PLAN.md` Milestone E. A fresh database starts
> **empty** — an earlier `init_db` seeded invented model rows; it no longer does.

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
   venv/bin/python -c "from learning.database import LearningDatabase; LearningDatabase()"
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
