#!/usr/bin/env python3
"""Initialize the learning database with the schema."""

import sqlite3
from pathlib import Path
from typing import Optional


def init_db(learning_dir: str, db_path: str = "solver.db", schema_path: Optional[str] = None) -> None:
    """Initialize the database with the schema.
    
    Args:
        learning_dir: Path to the learning directory
        db_path: Path to the database file to create/update
        schema_path: Optional path to the schema SQL file. If None, uses schema.sql from the learning module
    """
    # Get absolute paths
    learning_dir = Path(learning_dir).resolve()
    db_path = learning_dir / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if schema_path is None:
        schema_path = learning_dir / 'schema.sql'
    else:
        schema_path = Path(schema_path).resolve()
    
    print(f"Initializing database at {db_path}")
    print(f"Using schema from {schema_path}")
    
    # Read schema SQL
    with open(schema_path) as f:
        schema_sql = f.read()
    
    # Connect and initialize
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        seed_model_performance(conn)
    
    print("Database initialized successfully!")


def seed_model_performance(conn):
    """Seed the model_performance table with some default data."""
    try:
        # Check if the model_performance table is empty
        cursor = conn.execute("SELECT COUNT(*) FROM model_performance")
        count = cursor.fetchone()[0]
        if count == 0:
            models = [
                {"model_name": "codellama-7b-instruct", "problem_type": "general", "role": "primary", "success_rate": 0.5, "quality_score": 5.0, "response_time": 10.0, "cost": 0.0},
                {"model_name": "codellama-7b-instruct", "problem_type": "general", "role": "reviewer", "success_rate": 0.5, "quality_score": 5.0, "response_time": 10.0, "cost": 0.0},
                {"model_name": "codellama-7b-instruct", "problem_type": "general", "role": "validator", "success_rate": 0.5, "quality_score": 5.0, "response_time": 10.0, "cost": 0.0},
            ]
            with conn:
                for model in models:
                    conn.execute(
                        """
                        INSERT INTO model_performance (model_name, problem_type, role, success_rate, quality_score, response_time, cost, avg_quality_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            model["model_name"],
                            model["problem_type"],
                            model["role"],
                            model["success_rate"],
                            model["quality_score"],
                            model["response_time"],
                            model["cost"],
                            model["quality_score"],  # Use quality_score as initial avg_quality_score
                        ),
                    )
    except Exception as e:
        print(f"Error seeding model performance data: {e}")


if __name__ == "__main__":
    # Get the directory this script is in
    current_dir = Path(__file__).parent.resolve()
    
    # Initialize just the solver.db
    init_db(current_dir, current_dir / "solver.db", current_dir / "schema.sql")
