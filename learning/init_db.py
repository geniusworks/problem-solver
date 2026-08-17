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
    
    # Connect and initialize. A fresh database starts EMPTY on purpose: this is a
    # measurement store, and every row in it must be a measurement. An earlier
    # version seeded model_performance with invented numbers (a 0.5 success rate
    # and 5.0 quality for "codellama-7b-instruct" -- not even a valid Ollama tag),
    # which is exactly the asserted-not-measured data this project exists to
    # avoid. Cold start is handled where it belongs: _get_top_models falls back
    # to the installed models when the table has nothing to rank.
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)

    print("Database initialized successfully!")


if __name__ == "__main__":
    # Get the directory this script is in
    current_dir = Path(__file__).parent.resolve()
    
    # Initialize just the solver.db
    init_db(current_dir, current_dir / "solver.db", current_dir / "schema.sql")
