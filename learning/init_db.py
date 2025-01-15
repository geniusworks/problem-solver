#!/usr/bin/env python3
"""Initialize the learning database with the schema."""

import sqlite3
from pathlib import Path


def init_db(db_path: str = "solver.db", schema_path: str = "schema.sql") -> None:
    """Initialize the database with the schema.
    
    Args:
        db_path: Path to the database file to create/update
        schema_path: Path to the schema SQL file
    """
    # Get absolute paths
    db_path = Path(db_path).resolve()
    schema_path = Path(schema_path).resolve()
    
    print(f"Initializing database at {db_path}")
    print(f"Using schema from {schema_path}")
    
    # Read schema SQL
    with open(schema_path) as f:
        schema_sql = f.read()
    
    # Connect and initialize
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()
    
    print("Database initialized successfully!")


if __name__ == "__main__":
    # Get the directory this script is in
    current_dir = Path(__file__).parent.resolve()
    
    # Initialize just the solver.db
    init_db(current_dir / "solver.db", current_dir / "schema.sql")
