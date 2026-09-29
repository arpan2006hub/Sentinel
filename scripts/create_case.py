#!/usr/bin/env python3
"""
create_case.py — Placeholder

This script will eventually create a new investigation case via the backend API.

Currently NOT IMPLEMENTED.

Usage (future):
    python scripts/create_case.py --title "Case Q1-2026" --description "Suspected data exfiltration"

Requirements:
    - Backend API running
    - VITE_API_BASE_URL or BACKEND_HOST/BACKEND_PORT configured
"""

import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Create a new investigation case (placeholder)")
    parser.add_argument("--title", required=True, help="Case title")
    parser.add_argument("--description", default="", help="Case description")
    args = parser.parse_args()

    print(f"[create_case] NOT YET IMPLEMENTED")
    print(f"[create_case] Would create case:")
    print(f"  Title: {args.title}")
    print(f"  Description: {args.description}")
    print("")
    print("Required:")
    print("  - Backend API running at VITE_API_BASE_URL or http://localhost:8000")
    print("  - POST /cases endpoint implemented")
    sys.exit(1)

if __name__ == "__main__":
    main()