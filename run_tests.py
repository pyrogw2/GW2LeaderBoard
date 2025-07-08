#!/usr/bin/env python3
"""
Test runner for GW2 WvW Leaderboards automated tests.
Provides convenient interface to run different test suites.
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_quick_tests():
    """Run quick regression tests."""
    print("🚀 Running quick regression tests...")
    from tests.test_quick_regression import run_quick_tests
    return run_quick_tests()


def run_full_tests():
    """Run comprehensive functionality tests."""
    print("🔍 Running comprehensive functionality tests...")
    print("⚠️  This will generate a test web UI and may take 2-3 minutes...")
    from tests.test_web_ui_functionality import run_tests
    return run_tests()


def run_all_tests():
    """Run all test suites."""
    print("🧪 Running all test suites...\n")
    
    # Run quick tests first
    quick_success = run_quick_tests()
    
    if not quick_success:
        print("\n❌ Quick tests failed. Skipping comprehensive tests.")
        return False
    
    print("\n" + "="*60 + "\n")
    
    # Run comprehensive tests
    full_success = run_full_tests()
    
    return quick_success and full_success


def check_environment():
    """Check that the test environment is properly set up."""
    issues = []
    
    # Check database exists
    if not os.path.exists("gw2_comprehensive.db"):
        issues.append("❌ gw2_comprehensive.db not found")
    
    # Check required Python modules
    try:
        import sqlite3
        import json
        import re
        import tempfile
        import unittest
    except ImportError as e:
        issues.append(f"❌ Missing required Python module: {e}")
    
    # Check project structure
    required_dirs = ["src/gw2_leaderboard", "tests"]
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            issues.append(f"❌ Missing directory: {dir_path}")
    
    # Check key files
    required_files = ["generate_web_ui.py", "src/gw2_leaderboard/web/parallel_processing.py"]
    for file_path in required_files:
        if not os.path.exists(file_path):
            issues.append(f"❌ Missing file: {file_path}")
    
    if issues:
        print("Environment check failed:")
        for issue in issues:
            print(f"  {issue}")
        print("\nPlease run from the project root directory with a valid database.")
        return False
    
    print("✅ Environment check passed")
    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(
        description="GW2 WvW Leaderboards Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Suites:
  quick    - Fast regression tests (30 seconds)
           - Database schema and import checks
           - APM data validation
           - Date filtering logic
           
  full     - Comprehensive functionality tests (2-3 minutes)
           - Generates test web UI
           - Validates date filtering differences
           - Tests modal, guild filter, latest change
           - Checks APM calculation accuracy
           
  all      - Run both quick and full test suites

Examples:
  python run_tests.py quick          # Quick regression check
  python run_tests.py full           # Full functionality test
  python run_tests.py all            # Complete test suite
  python run_tests.py --check        # Environment check only
        """
    )
    
    parser.add_argument(
        "suite",
        nargs="?",
        choices=["quick", "full", "all"],
        default="quick",
        help="Test suite to run (default: quick)"
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check environment setup and exit"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print("🧪 GW2 WvW Leaderboards Test Runner")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        return 1
    
    if args.check:
        print("✅ Environment check completed successfully")
        return 0
    
    print()
    start_time = time.time()
    
    # Run selected test suite
    if args.suite == "quick":
        success = run_quick_tests()
    elif args.suite == "full":
        success = run_full_tests()
    elif args.suite == "all":
        success = run_all_tests()
    else:
        print(f"❌ Unknown test suite: {args.suite}")
        return 1
    
    # Print summary
    duration = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"⏱️  Tests completed in {duration:.1f} seconds")
    
    if success:
        print("🎉 All tests passed!")
        print("\n💡 Tip: Run 'python run_tests.py full' for comprehensive validation")
        return 0
    else:
        print("💥 Some tests failed!")
        print("\n🔧 Check the output above for specific failures")
        return 1


if __name__ == "__main__":
    sys.exit(main())