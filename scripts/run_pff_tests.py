#!/usr/bin/env python3
"""
Quick runner for common PFF scraper test scenarios.

Provides preset test configurations without needing to remember command-line arguments.

Usage:
    poetry run python run_pff_tests.py [scenario]

Available Scenarios:
    1  Quick     - Single page scrape (fastest, ~10 seconds)
    2  Standard  - 3 pages with cache (default, ~30 seconds)
    3  Full      - 5 pages with all tests (comprehensive, ~60 seconds)
    4  Cache     - Test cache functionality only
    5  Visual    - Single page with browser visible
    6  Debug     - No cache, single page with detailed logging
"""

import sys
import subprocess
import argparse
from typing import List

SCENARIOS = {
    "1": {
        "name": "Quick Test",
        "description": "Single page scrape (fastest)",
        "args": ["--test", "single"],
    },
    "2": {
        "name": "Standard Test",
        "description": "3 pages with cache (recommended)",
        "args": ["--test", "multi", "--pages", "3"],
    },
    "3": {
        "name": "Full Test",
        "description": "5 pages with all tests",
        "args": ["--test", "all", "--pages", "5"],
    },
    "4": {
        "name": "Cache Test",
        "description": "Test cache functionality",
        "args": ["--test", "cache"],
    },
    "5": {
        "name": "Visual Test",
        "description": "Single page with browser visible",
        "args": ["--test", "single", "--no-headless"],
    },
    "6": {
        "name": "Debug Test",
        "description": "No cache, single page",
        "args": ["--test", "single", "--no-cache"],
    },
}


def print_menu():
    """Print scenario menu."""
    print("\n" + "=" * 70)
    print("PFF SCRAPER TEST SCENARIOS".center(70))
    print("=" * 70)
    
    for key, config in sorted(SCENARIOS.items()):
        print(f"\n  [{key}] {config['name']}")
        print(f"      {config['description']}")
        args_str = " ".join(config["args"])
        print(f"      Args: {args_str}")
    
    print("\n  [0] Exit")
    print("\n" + "=" * 70 + "\n")


def run_test(scenario_num: str) -> int:
    """Run selected test scenario."""
    if scenario_num not in SCENARIOS:
        print(f"❌ Invalid scenario: {scenario_num}")
        return 1
    
    config = SCENARIOS[scenario_num]
    
    print(f"\n🚀 Running: {config['name']}")
    print(f"   {config['description']}\n")
    
    cmd = ["poetry", "run", "python", "test_pff_scraper.py"] + config["args"]
    
    print(f"   Command: {' '.join(cmd)}\n")
    print("-" * 70 + "\n")
    
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Quick runner for PFF scraper test scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("scenario", nargs="?", help="Scenario number (1-6) or name")
    
    args = parser.parse_args()
    
    if args.scenario:
        # Direct scenario from command line
        if args.scenario.lower() in ("0", "exit", "quit"):
            print("Exiting...")
            return 0
        
        # Try numeric
        if args.scenario.isdigit():
            return run_test(args.scenario)
        
        # Try by name
        for key, config in SCENARIOS.items():
            if config["name"].lower() == args.scenario.lower():
                return run_test(key)
        
        print(f"❌ Unknown scenario: {args.scenario}")
        print("\nValid scenarios: 1-6 or names like 'Quick', 'Standard', 'Full', etc.")
        return 1
    
    # Interactive menu
    while True:
        print_menu()
        
        choice = input("Select scenario (0-6): ").strip()
        
        if choice == "0":
            print("✓ Exiting")
            return 0
        
        result = run_test(choice)
        
        if result == 0:
            print("\n✓ Test completed successfully")
        else:
            print(f"\n❌ Test failed with exit code {result}")
        
        continue_choice = input("\nRun another test? (y/n): ").strip().lower()
        if continue_choice != "y":
            print("✓ Exiting")
            return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
