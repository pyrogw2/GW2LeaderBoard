#!/usr/bin/env python3
"""
Quick regression tests for GW2 WvW Leaderboards.
Lightweight tests that can be run frequently during development.
"""

import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class QuickRegressionTests(unittest.TestCase):
    """Quick regression tests for core functionality."""
    
    def setUp(self):
        """Set up test database connection."""
        self.db_path = "gw2_comprehensive.db"
        if not os.path.exists(self.db_path):
            self.skipTest("Database not found")
    
    def test_database_schema_integrity(self):
        """Test that required database tables and columns exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        required_tables = ["player_performances", "glicko_ratings"]
        for table in required_tables:
            self.assertIn(table, tables, f"Required table {table} missing")
        
        # Check player_performances columns
        cursor.execute("PRAGMA table_info(player_performances)")
        columns = {row[1] for row in cursor.fetchall()}
        
        required_columns = [
            "account_name", "profession", "timestamp", "target_dps",
            "apm_total", "apm_no_auto", "stability_gen_per_sec"
        ]
        
        for column in required_columns:
            self.assertIn(column, columns, f"Required column {column} missing from player_performances")
        
        conn.close()
    
    def test_apm_data_exists_in_database(self):
        """Test that APM data exists in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for non-zero APM data
        cursor.execute("SELECT COUNT(*) FROM player_performances WHERE apm_total > 0")
        apm_count = cursor.fetchone()[0]
        
        self.assertGreater(apm_count, 0, "No APM data found in database")
        
        # Check recent APM data (last 60 days)
        cursor.execute("""
            SELECT COUNT(*) FROM player_performances 
            WHERE apm_total > 0 
            AND timestamp >= strftime('%Y%m%d%H%M', 'now', '-60 days')
        """)
        recent_apm_count = cursor.fetchone()[0]
        
        self.assertGreater(recent_apm_count, 0, "No recent APM data found")
        
        conn.close()
    
    def test_date_filtering_logic(self):
        """Test that date filtering returns different data sets."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get counts for different time periods
        cursor.execute("SELECT COUNT(*) FROM player_performances")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM player_performances 
            WHERE timestamp >= strftime('%Y%m%d%H%M', 'now', '-30 days')
        """)
        thirty_day_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM player_performances 
            WHERE timestamp >= strftime('%Y%m%d%H%M', 'now', '-60 days')
        """)
        sixty_day_count = cursor.fetchone()[0]
        
        # Verify logical relationships
        self.assertGreaterEqual(total_count, sixty_day_count, "Total should be >= 60-day count")
        self.assertGreaterEqual(sixty_day_count, thirty_day_count, "60-day should be >= 30-day count")
        
        # Verify we have some recent data
        self.assertGreater(thirty_day_count, 0, "No data in last 30 days")
        
        conn.close()
    
    def test_profession_metrics_configuration(self):
        """Test that profession metrics are properly configured."""
        try:
            from src.gw2_leaderboard.core.glicko_rating_system import PROFESSION_METRICS
        except ImportError:
            from gw2_leaderboard.core.glicko_rating_system import PROFESSION_METRICS
        
        # Check that key professions exist
        key_professions = ["Firebrand", "Chronomancer", "Druid", "Scourge"]
        for profession in key_professions:
            self.assertIn(profession, PROFESSION_METRICS, f"Missing profession: {profession}")
            
            config = PROFESSION_METRICS[profession]
            self.assertIn("metrics", config, f"Missing metrics for {profession}")
            self.assertIn("weights", config, f"Missing weights for {profession}")
            
            # Check metrics and weights match
            self.assertEqual(
                len(config["metrics"]), len(config["weights"]),
                f"Metrics and weights length mismatch for {profession}"
            )
    
    def test_parallel_processing_import(self):
        """Test that parallel processing module imports correctly."""
        try:
            from src.gw2_leaderboard.web.parallel_processing import calculate_simple_profession_ratings_fast_filter
        except ImportError:
            try:
                from gw2_leaderboard.web.parallel_processing import calculate_simple_profession_ratings_fast_filter
            except ImportError:
                self.fail("Could not import parallel_processing module")
        
        # Test function exists and is callable
        self.assertTrue(callable(calculate_simple_profession_ratings_fast_filter))
    
    def test_web_ui_generation_imports(self):
        """Test that web UI generation imports work."""
        # Test the actual web UI generation function
        try:
            from src.gw2_leaderboard.web.generate_web_ui import main
        except ImportError:
            try:
                from gw2_leaderboard.web.generate_web_ui import main
            except ImportError:
                self.fail("Could not import generate_web_ui main function")
        
        self.assertTrue(callable(main), "generate_web_ui main function should be callable")
        
        # Test key data processing imports
        try:
            from src.gw2_leaderboard.web.data_processing import get_glicko_leaderboard_data_with_sql_filter
        except ImportError:
            try:
                from gw2_leaderboard.web.data_processing import get_glicko_leaderboard_data_with_sql_filter
            except ImportError:
                self.fail("Could not import data_processing functions")
    
    def test_sample_apm_calculation(self):
        """Test APM calculation on a small sample."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get a sample player with APM data
        cursor.execute("""
            SELECT account_name, profession, apm_total, apm_no_auto
            FROM player_performances 
            WHERE apm_total > 0 
            LIMIT 1
        """)
        
        sample = cursor.fetchone()
        if not sample:
            self.skipTest("No APM data available for testing")
        
        account_name, profession, apm_total, apm_no_auto = sample
        
        # Test the calculation logic used in profession leaderboards
        cursor.execute("""
            SELECT AVG(apm_total), AVG(apm_no_auto)
            FROM player_performances
            WHERE account_name = ? AND profession = ? AND apm_total > 0
        """, (account_name, profession))
        
        result = cursor.fetchone()
        self.assertIsNotNone(result[0], "APM calculation returned None")
        self.assertGreater(result[0], 0, "APM calculation should be > 0")
        self.assertGreater(result[1], 0, "APM no-auto calculation should be > 0")
        
        conn.close()
    
    def test_guild_data_exists(self):
        """Test that guild data is available if enabled."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if guild_members table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
        guild_table_exists = cursor.fetchone() is not None
        
        if guild_table_exists:
            # If guild table exists, check it has data
            cursor.execute("SELECT COUNT(*) FROM guild_members")
            guild_count = cursor.fetchone()[0]
            self.assertGreater(guild_count, 0, "Guild members table exists but is empty")
        
        conn.close()
    
    def test_recent_data_exists(self):
        """Test that we have recent performance data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for data in last 7 days
        cursor.execute("""
            SELECT COUNT(*) FROM player_performances 
            WHERE timestamp >= strftime('%Y%m%d%H%M', 'now', '-7 days')
        """)
        
        recent_count = cursor.fetchone()[0]
        self.assertGreater(recent_count, 0, "No performance data in last 7 days")
        
        conn.close()


def run_quick_tests():
    """Run the quick regression test suite."""
    # Check if database exists
    if not os.path.exists("gw2_comprehensive.db"):
        print("❌ gw2_comprehensive.db not found. Please run from project root directory.")
        return False
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(QuickRegressionTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All {result.testsRun} quick regression tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors out of {result.testsRun} tests")
        for test, error in result.failures + result.errors:
            print(f"  - {test}: {error.split(chr(10))[-2] if error else 'Unknown error'}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run quick regression tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    success = run_quick_tests()
    sys.exit(0 if success else 1)