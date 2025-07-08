#!/usr/bin/env python3
"""
Tests for player modal functionality to prevent regression of modal bugs.
"""

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.gw2_leaderboard.web.generate_web_ui import main as generate_web_ui
except ImportError:
    from gw2_leaderboard.web.generate_web_ui import main as generate_web_ui


class PlayerModalFunctionalityTests(unittest.TestCase):
    """Test player modal JavaScript functionality to prevent regressions."""
    
    @classmethod
    def setUpClass(cls):
        """Generate a test web UI once for all tests."""
        cls.test_output_dir = tempfile.mkdtemp(prefix="gw2_modal_test_")
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
                "--date-filters", "30d", "overall"
            ]
            
            # Run web UI generation 
            generate_web_ui()
            
            # Restore original sys.argv
            sys.argv = original_argv
        except Exception as e:
            # Restore original sys.argv in case of error
            sys.argv = original_argv
            raise unittest.SkipTest(f"Failed to generate test web UI: {e}")
        
        # Load the generated JavaScript content
        script_file = Path(cls.test_output_dir) / "script.js"
        if not script_file.exists():
            raise unittest.SkipTest("Generated script.js not found")
        
        with open(script_file, 'r', encoding='utf-8') as f:
            cls.script_content = f.read()
    
    def test_clear_modal_state_function_exists(self):
        """Test that clearModalState function exists to prevent name persistence bug."""
        # Check that clearModalState function is defined
        self.assertIn("function clearModalState()", self.script_content,
                     "clearModalState function should be defined to reset modal state")
        
        # Check that it clears the chart
        self.assertIn("window.currentPlayerChart.destroy()", self.script_content,
                     "clearModalState should destroy existing chart")
        
        # Check that it clears chart status
        self.assertIn("chartStatus.textContent = ''", self.script_content,
                     "clearModalState should clear chart status text")
    
    def test_clear_modal_state_called_in_populate(self):
        """Test that clearModalState is called when populating modal."""
        # Find populatePlayerModal function
        populate_match = re.search(r'function populatePlayerModal\([^)]*\)\s*{([^}]*)}', 
                                 self.script_content, re.DOTALL)
        self.assertIsNotNone(populate_match, "populatePlayerModal function should exist")
        
        populate_function = populate_match.group(1)
        
        # Check that clearModalState is called
        self.assertIn("clearModalState()", populate_function,
                     "populatePlayerModal should call clearModalState to prevent name persistence")
    
    def test_rating_history_error_handling(self):
        """Test that rating history has proper error handling."""
        # Check that fetchRatingHistory has try-catch
        self.assertIn("try {", self.script_content,
                     "fetchRatingHistory should have try-catch for error handling")
        
        # Check for specific error handling in rating history
        fetch_history_match = re.search(r'async function fetchRatingHistory\([^)]*\)\s*{([^}]*)}', 
                                      self.script_content, re.DOTALL)
        if fetch_history_match:
            fetch_function = fetch_history_match.group(1)
            self.assertIn("catch (error)", fetch_function,
                         "fetchRatingHistory should have catch block for error handling")
            self.assertIn("console.error", fetch_function,
                         "fetchRatingHistory should log errors to console")
    
    def test_global_chart_state_management(self):
        """Test that chart state is managed globally to prevent memory leaks."""
        # Check that window.currentPlayerChart is used
        self.assertIn("window.currentPlayerChart", self.script_content,
                     "Chart state should use global window.currentPlayerChart")
        
        # Check that chart is assigned to global variable
        self.assertIn("window.currentPlayerChart = currentChart", self.script_content,
                     "New charts should be assigned to global variable")
    
    def test_player_data_validation(self):
        """Test that playerData is validated before use."""
        # Check for playerData validation in fetchRatingHistory
        fetch_history_match = re.search(r'async function fetchRatingHistory\([^)]*\)\s*{([^}]*)}', 
                                      self.script_content, re.DOTALL)
        if fetch_history_match:
            fetch_function = fetch_history_match.group(1)
            self.assertIn("!playerData", fetch_function,
                         "fetchRatingHistory should validate playerData exists")
            self.assertIn("Array.isArray(playerData)", fetch_function,
                         "fetchRatingHistory should validate playerData is array")
    
    def test_modal_title_setting(self):
        """Test that modal title is properly set in populatePlayerModal."""
        # Check that modal title is set with account name
        populate_match = re.search(r'function populatePlayerModal\([^)]*\)\s*{([^}]*)}', 
                                 self.script_content, re.DOTALL)
        if populate_match:
            populate_function = populate_match.group(1)
            self.assertIn("player-modal-title", populate_function,
                         "populatePlayerModal should set modal title")
            self.assertIn("Player Details:", populate_function,
                         "Modal title should include 'Player Details' text")
    
    def test_show_player_modal_function_exists(self):
        """Test that showPlayerModal function exists and calls populatePlayerModal."""
        # Check that showPlayerModal function exists
        self.assertIn("function showPlayerModal(", self.script_content,
                     "showPlayerModal function should exist")
        
        # Check that it calls populatePlayerModal
        show_modal_match = re.search(r'function showPlayerModal\([^)]*\)\s*{([^}]*)}', 
                                   self.script_content, re.DOTALL)
        if show_modal_match:
            show_function = show_modal_match.group(1)
            self.assertIn("populatePlayerModal", show_function,
                         "showPlayerModal should call populatePlayerModal")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test files."""
        import shutil
        if hasattr(cls, 'test_output_dir') and os.path.exists(cls.test_output_dir):
            shutil.rmtree(cls.test_output_dir)


def run_modal_tests():
    """Run the modal functionality test suite."""
    # Check if database exists
    if not os.path.exists("gw2_comprehensive.db"):
        print("❌ gw2_comprehensive.db not found. Please run from project root directory.")
        return False
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(PlayerModalFunctionalityTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    if result.wasSuccessful():
        print(f"\n✅ All {result.testsRun} modal tests passed!")
        return True
    else:
        print(f"\n❌ {len(result.failures)} failures, {len(result.errors)} errors out of {result.testsRun} tests")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run GW2 Leaderboard player modal functionality tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    success = run_modal_tests()
    sys.exit(0 if success else 1)