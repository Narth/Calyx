"""
Validate JSON schemas in the repo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_schema_file(schema_path: Path) -> bool:
    """Validate a single schema file."""
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        
        # Basic validation - check it's valid JSON and has $schema
        if "$schema" not in schema:
            print(f"WARNING: {schema_path} missing $schema field")
            return False
        
        print(f"✓ {schema_path} is valid")
        return True
    except json.JSONDecodeError as e:
        print(f"ERROR: {schema_path} is not valid JSON: {e}")
        return False
    except Exception as e:
        print(f"ERROR: {schema_path} validation failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-dir", default="telemetry/envelopes")
    args = parser.parse_args()
    
    schema_dir = Path(args.schema_dir)
    if not schema_dir.exists():
        print(f"Schema directory not found: {schema_dir}")
        return
    
    schemas = list(schema_dir.glob("*.json"))
    if not schemas:
        print("No schema files found")
        return
    
    all_valid = True
    for schema_path in schemas:
        if not validate_schema_file(schema_path):
            all_valid = False
    
    if not all_valid:
        exit(1)


if __name__ == "__main__":
    main()
