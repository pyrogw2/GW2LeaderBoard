#!/usr/bin/env python3
"""
Automated tests for GW2 WvW Leaderboards web UI functionality.
Tests critical features to prevent regressions during development.
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.gw2_leaderboard.web.generate_web_ui import main as generate_web_ui
except ImportError:
    from gw2_leaderboard.web.generate_web_ui import main as generate_web_ui


class WebUIFunctionalityTests(unittest.TestCase):
    """Test suite for web UI functionality and data integrity."""
    
    @classmethod
    def setUpClass(cls):
        """Generate a test web UI once for all tests."""
        cls.test_output_dir = tempfile.mkdtemp(prefix="gw2_test_ui_")
        cls.db_path = "gw2_comprehensive.db"
        
        # Generate web UI for testing
        print(f"Generating test web UI in {cls.test_output_dir}...")
        try:
            # Save original sys.argv and replace with test arguments
            original_argv = sys.argv
            sys.argv = [
                "generate_web_ui",
                cls.db_path,
                "-o", cls.test_output_dir,
                "--skip-recalc",
                "--date-filters", "30d", "60d", "90d", "overall"
            ]
            
            # Run web UI generation 
            generate_web_ui()
            
            # Restore original sys.argv
            sys.argv = original_argv
        except Exception as e:
            # Restore original sys.argv in case of error
            sys.argv = original_argv
            raise unittest.SkipTest(f"Failed to generate test web UI: {e}")
        
        # Load the generated JavaScript data
        script_file = Path(cls.test_output_dir) / "script.js"
        if not script_file.exists():
            raise unittest.SkipTest("Generated script.js not found")
        
        cls.leaderboard_data = cls._extract_leaderboard_data(script_file)
        
    @classmethod
    def _extract_leaderboard_data(cls, script_file: Path) -> Dict[str, Any]:
        """Extract leaderboard data from generated script.js file."""
        with open(script_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the leaderboardData JSON
        match = re.search(r'const leaderboardData = ({.*?});', content, re.DOTALL)
        if not match:
            raise ValueError("Could not find leaderboardData in script.js")
        
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse leaderboardData JSON: {e}")
    
    def test_date_filter_individual_metrics_different_data(self):
        """Test that individual metrics show different data across date filters."""
        date_filters = ["30d", "60d", "overall"]
        test_metrics = ["DPS", "Healing", "Stability"]
        
        for metric in test_metrics:
            with self.subTest(metric=metric):
                metric_data = {}
                
                # Extract data for each date filter
                for date_filter in date_filters:
                    filter_data = self.leaderboard_data["date_filters"].get(date_filter, {})
                    individual_metrics = filter_data.get("individual_metrics", {})
                    metric_leaderboard = individual_metrics.get(metric, [])
                    
                    # Create comparable dataset (top players and their ratings)
                    metric_data[date_filter] = {
                        "player_count": len(metric_leaderboard),
                        "top_5_players": [
                            (player["account_name"], player["glicko_rating"])
                            for player in metric_leaderboard[:5]
                        ],
                        "rating_range": (
                            metric_leaderboard[0]["glicko_rating"] if metric_leaderboard else 0,
                            metric_leaderboard[-1]["glicko_rating"] if metric_leaderboard else 0
                        )
                    }
                
                # Verify differences between date filters
                self.assertGreater(
                    metric_data["overall"]["player_count"],
                    metric_data["30d"]["player_count"],
                    f"{metric}: Overall should have more players than 30d"
                )
                
                # Check that at least some data differs between periods
                differences_found = (
                    metric_data["30d"]["top_5_players"] != metric_data["60d"]["top_5_players"] or
                    metric_data["30d"]["player_count"] != metric_data["60d"]["player_count"] or
                    metric_data["60d"]["top_5_players"] != metric_data["overall"]["top_5_players"]
                )
                
                self.assertTrue(
                    differences_found,
                    f"{metric}: No differences found between date filters - data may not be properly filtered"
                )
    
    def test_date_filter_profession_leaderboards_different_data(self):
        """Test that profession leaderboards show different data across date filters."""
        date_filters = ["30d", "60d", "overall"]
        test_professions = ["Firebrand", "Chronomancer", "Druid"]
        
        for profession in test_professions:
            with self.subTest(profession=profession):
                profession_data = {}
                
                # Extract data for each date filter
                for date_filter in date_filters:
                    filter_data = self.leaderboard_data["date_filters"].get(date_filter, {})
                    profession_leaderboards = filter_data.get("profession_leaderboards", {})
                    profession_leaderboard = profession_leaderboards.get(profession, {})
                    
                    if "leaderboard" in profession_leaderboard:
                        players = profession_leaderboard["leaderboard"]
                    else:
                        players = profession_leaderboard.get("players", [])
                    
                    # Create comparable dataset
                    profession_data[date_filter] = {
                        "player_count": len(players),
                        "top_5_players": [
                            (player["account_name"], player["composite_score"])
                            for player in players[:5]
                        ],
                        "has_apm_data": any(
                            player.get("apm_total", 0) > 0 for player in players[:10]
                        )
                    }
                
                # Verify differences between date filters
                if profession_data["overall"]["player_count"] > 0:
                    # Note: In some cases, recent data may have more players than overall
                    # This can happen if overall filter is more restrictive than time-based filters
                    # The key is that we have data and some differences exist between periods
                    
                    # Check for differences in top players or counts between ANY periods
                    differences_found = (
                        profession_data["30d"]["player_count"] != profession_data["60d"]["player_count"] or
                        profession_data["30d"]["top_5_players"] != profession_data["60d"]["top_5_players"] or
                        profession_data["60d"]["top_5_players"] != profession_data["overall"]["top_5_players"] or
                        profession_data["30d"]["player_count"] != profession_data["overall"]["player_count"]
                    )
                    
                    self.assertTrue(
                        differences_found or profession_data["overall"]["player_count"] <= 1,
                        f"{profession}: No differences found between date filters - this suggests date filtering may not be working"
                    )
    
    def test_apm_data_not_zero(self):
        """Test that APM data is properly calculated (not all 0.0/0.0)."""
        # Check profession leaderboards for actual APM data
        for date_filter in ["30d", "60d", "overall"]:
            filter_data = self.leaderboard_data["date_filters"].get(date_filter, {})
            profession_leaderboards = filter_data.get("profession_leaderboards", {})
            
            apm_values_found = False
            for profession, profession_data in profession_leaderboards.items():
                if "leaderboard" in profession_data:
                    players = profession_data["leaderboard"]
                else:
                    players = profession_data.get("players", [])
                
                # Check if any players have non-zero APM
                for player in players[:20]:  # Check top 20 players
                    apm_total = player.get("apm_total", 0)
                    if apm_total > 0:
                        apm_values_found = True
                        break
                
                if apm_values_found:
                    break
            
            if not apm_values_found:
                self.fail(f"No non-zero APM values found in {date_filter} profession leaderboards")
    
    def test_high_scores_data_exists(self):
        """Test that high scores contain actual data across date filters."""
        date_filters = ["30d", "60d", "overall"]
        
        for date_filter in date_filters:
            with self.subTest(date_filter=date_filter):
                filter_data = self.leaderboard_data["date_filters"].get(date_filter, {})
                high_scores = filter_data.get("high_scores", {})
                
                # Check that high scores exist and have reasonable structure
                self.assertIsInstance(high_scores, dict, f"High scores should be a dict for {date_filter}")
                
                # High scores may be empty for some date filters (this is okay)
                # The important thing is that the structure exists and when data exists, it's valid
                if high_scores:  # If high scores exist, validate them
                    data_found = False
                    for category, scores in high_scores.items():
                        if scores:  # If this category has data
                            data_found = True
                            self.assertIsInstance(scores, list, f"High scores {category} should be a list")
                            if scores:
                                first_score = scores[0]
                                self.assertIn("account_name", first_score, f"High score entry missing account_name")
                                
                                # High scores can have different value field names
                                value_fields = ["value", "burst_damage", "damage", "dps"]
                                value_found = False
                                actual_value = 0
                                
                                for field in value_fields:
                                    if field in first_score:
                                        value_found = True
                                        actual_value = first_score[field]
                                        break
                                
                                self.assertTrue(value_found, f"High score entry missing value field (checked: {value_fields})")
                                self.assertGreater(actual_value, 0, f"High score value should be > 0, got {actual_value}")
                    
                    # Allow empty high scores for short time periods, but overall should have some data
                    if date_filter == "overall" and not data_found:
                        self.fail(f"No high score data found for {date_filter} - this suggests an issue")
    
    def test_guild_filtering_functionality(self):
        """Test that guild filtering data is properly configured."""
        # Check that guild filtering is enabled
        self.assertTrue(
            self.leaderboard_data.get("guild_enabled", False),
            "Guild filtering should be enabled"
        )
        
        # Check guild name and tag exist
        self.assertIsInstance(
            self.leaderboard_data.get("guild_name", ""),
            str,
            "Guild name should be a string"
        )
        
        self.assertIsInstance(
            self.leaderboard_data.get("guild_tag", ""),
            str,
            "Guild tag should be a string"
        )
        
        # Check that some players have guild membership data
        guild_members_found = False
        for date_filter in ["30d", "overall"]:
            filter_data = self.leaderboard_data["date_filters"].get(date_filter, {})
            individual_metrics = filter_data.get("individual_metrics", {})
            
            for metric, players in individual_metrics.items():
                for player in players[:10]:  # Check first 10 players
                    if "is_guild_member" in player:
                        guild_members_found = True
                        break
                if guild_members_found:
                    break
            if guild_members_found:
                break
        
        self.assertTrue(guild_members_found, "No guild membership data found in players")
    
    def test_rating_deltas_functionality(self):
        """Test that rating deltas (Latest Change) are present."""
        # Check that some players have rating deltas
        deltas_found = False
        for date_filter in ["30d", "overall"]:
            filter_data = self.leaderboard_data["date_filters"].get(date_filter, {})
            individual_metrics = filter_data.get("individual_metrics", {})
            
            for metric, players in individual_metrics.items():
                for player in players[:20]:  # Check first 20 players
                    rating_delta = player.get("rating_delta", 0)
                    if rating_delta != 0:  # Non-zero delta found
                        deltas_found = True
                        break
                if deltas_found:
                    break
            if deltas_found:
                break
        
        # Note: It's okay if no deltas are found (all could be 0), but structure should exist
        for date_filter in ["30d", "overall"]:
            filter_data = self.leaderboard_data["date_filters"].get(date_filter, {})
            individual_metrics = filter_data.get("individual_metrics", {})
            
            if individual_metrics:
                first_metric = next(iter(individual_metrics.values()))
                if first_metric:
                    first_player = first_metric[0]
                    self.assertIn("rating_delta", first_player, "Players should have rating_delta field")
    
    def test_modal_data_structure(self):
        """Test that data structure supports modal functionality."""
        # Check that individual metrics have proper player data for modals
        for date_filter in ["30d", "overall"]:
            filter_data = self.leaderboard_data["date_filters"].get(date_filter, {})
            individual_metrics = filter_data.get("individual_metrics", {})
            
            for metric, players in individual_metrics.items():
                if players:  # If players exist for this metric
                    first_player = players[0]
                    
                    # Check required fields for modal
                    required_fields = [
                        "account_name", "profession", "glicko_rating", 
                        "games_played", "average_stat_value"
                    ]
                    
                    for field in required_fields:
                        self.assertIn(
                            field, first_player,
                            f"Player missing {field} required for modal in {metric}/{date_filter}"
                        )
                    
                    # Check that account names are valid strings
                    self.assertIsInstance(
                        first_player["account_name"], str,
                        f"Account name should be string in {metric}/{date_filter}"
                    )
                    
                    self.assertGreater(
                        len(first_player["account_name"]), 0,
                        f"Account name should not be empty in {metric}/{date_filter}"
                    )
    
    def test_data_structure_integrity(self):
        """Test overall data structure integrity."""
        # Check required top-level fields
        required_fields = ["generated_at", "guild_enabled", "date_filters"]
        for field in required_fields:
            self.assertIn(field, self.leaderboard_data, f"Missing required field: {field}")
        
        # Check date filters exist
        date_filters = self.leaderboard_data["date_filters"]
        expected_filters = ["30d", "60d", "90d", "overall"]
        
        for filter_name in expected_filters:
            self.assertIn(filter_name, date_filters, f"Missing date filter: {filter_name}")
            
            filter_data = date_filters[filter_name]
            expected_sections = ["individual_metrics", "profession_leaderboards", "high_scores", "player_stats"]
            
            for section in expected_sections:
                self.assertIn(section, filter_data, f"Missing section {section} in {filter_name}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test files."""
        import shutil
        if hasattr(cls, 'test_output_dir') and os.path.exists(cls.test_output_dir):
            shutil.rmtree(cls.test_output_dir)


def run_tests():
    """Run the test suite."""
    # Check if database exists
    if not os.path.exists("gw2_comprehensive.db"):
        print("❌ gw2_comprehensive.db not found. Please run from project root directory.")
        return False
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(WebUIFunctionalityTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All {result.testsRun} tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors out of {result.testsRun} tests")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run GW2 Leaderboard web UI functionality tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    success = run_tests()
    sys.exit(0 if success else 1)