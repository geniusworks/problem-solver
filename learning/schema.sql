-- Schema for the problem solver learning database

-- Strategy results for each solution attempt
CREATE TABLE IF NOT EXISTS strategy_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id TEXT NOT NULL,  -- Format: YYYY_dayDD_partN
    timestamp TEXT NOT NULL,   -- ISO format
    strategies_used TEXT NOT NULL,  -- JSON array of strategy names
    success BOOLEAN NOT NULL,
    execution_time REAL,       -- In seconds
    memory_usage INTEGER,      -- In bytes
    attempts INTEGER,          -- Number of attempts before success/giving up
    failure_points TEXT,       -- JSON array of failure descriptions
    generation_time REAL,      -- Time to generate solution
    code_size INTEGER,         -- Size of solution in bytes
    UNIQUE(problem_id, timestamp)
);

-- Strategy weights and effectiveness
CREATE TABLE IF NOT EXISTS strategy_weights (
    strategy_name TEXT PRIMARY KEY,
    success_rate REAL NOT NULL,      -- 0.0 to 1.0
    avg_execution_time REAL,         -- In seconds
    avg_memory_usage INTEGER,        -- In bytes
    avg_attempts INTEGER,            -- Average attempts when this strategy is used
    total_uses INTEGER NOT NULL,     -- Total times this strategy was used
    last_updated TEXT NOT NULL,      -- ISO timestamp
    problem_types TEXT               -- JSON array of problem types this works well for
);

-- Problem characteristics and patterns
CREATE TABLE IF NOT EXISTS problem_characteristics (
    problem_id TEXT PRIMARY KEY,     -- Format: YYYY_dayDD_partN
    characteristics TEXT NOT NULL,    -- JSON object of problem features
    successful_strategies TEXT,       -- JSON array of strategies that worked
    solution_metrics TEXT,           -- JSON object with solution metrics
    attempt_history TEXT,            -- JSON array of attempt summaries
    last_updated TEXT NOT NULL       -- ISO timestamp
);

-- Model performance tracking
CREATE TABLE IF NOT EXISTS model_performance (
    model_name TEXT NOT NULL,
    problem_type TEXT NOT NULL,      -- Category of problem
    role TEXT NOT NULL,              -- Model's role (primary, reviewer, etc.)
    success_rate REAL NOT NULL,      -- successes/attempts once attempts > 0
    response_time REAL NOT NULL,
    cost REAL NOT NULL,
    quality_score REAL NOT NULL,     -- most recent attempt
    avg_quality_score REAL NOT NULL DEFAULT 0.0,  -- running mean over attempts
    attempts INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    UNIQUE(model_name, problem_type, role)
);

-- Collaborative improvement tracking
CREATE TABLE IF NOT EXISTS improvement_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id TEXT NOT NULL,
    iteration INTEGER NOT NULL,      -- Which improvement round
    model_name TEXT NOT NULL,        -- Model making the improvement
    improvement_type TEXT NOT NULL,  -- Type of improvement made
    impact_score REAL,              -- Improvement impact (0.0 to 1.0)
    timestamp TEXT NOT NULL,         -- ISO timestamp
    UNIQUE(problem_id, iteration, model_name)
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_strategy_results_problem 
ON strategy_results(problem_id);

CREATE INDEX IF NOT EXISTS idx_strategy_results_success 
ON strategy_results(success);

CREATE INDEX IF NOT EXISTS idx_model_performance_success 
ON model_performance(success_rate);

CREATE INDEX IF NOT EXISTS idx_improvement_history_problem 
ON improvement_history(problem_id, iteration);
