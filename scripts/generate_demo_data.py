#!/usr/bin/env python3
"""
generate_demo_data.py — Placeholder

This script will eventually generate synthetic demo data for development and testing.

Currently NOT IMPLEMENTED.

Usage (future):
    python scripts/generate_demo_data.py --cases 3 --events-per-case 100

Planned capabilities:
    - Generate synthetic cases
    - Generate synthetic canonical events conforming to event.schema.json
    - Generate synthetic evidence metadata (no actual files)
    - Optionally push to backend API or write JSON fixtures

Requirements:
    - jsonschema for validating against data/schemas/event.schema.json
    - faker or similar for synthetic data generation
"""

import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic demo data (placeholder)")
    parser.add_argument("--cases", type=int, default=3, help="Number of cases to generate")
    parser.add_argument("--events-per-case", type=int, default=100, help="Events per case")
    parser.add_argument("--output", default="data/sample/", help="Output directory")
    args = parser.parse_args()

    print(f"[generate_demo_data] NOT YET IMPLEMENTED")
    print(f"[generate_demo_data] Would generate:")
    print(f"  Cases: {args.cases}")
    print(f"  Events per case: {args.events_per_case}")
    print(f"  Output: {args.output}")
    print("")
    print("Required:")
    print("  - jsonschema for validation")
    print("  - faker or similar for synthetic data")
    print("  - Canonical event schema at data/schemas/event.schema.json")
    sys.exit(1)

if __name__ == "__main__":
    main()