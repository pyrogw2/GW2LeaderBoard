"""
Parallel processing functionality for GW2 WvW Leaderboards web UI generation.
Handles concurrent data generation, progress tracking, and multi-threaded processing.
"""

import json
import sqlite3
import os
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# Add current directory and parent directories to Python path to import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.extend([current_dir, parent_dir, grandparent_dir])

# Handle both relative and absolute imports
try:
    from ..core.glicko_rating_system import (
        PROFESSION_METRICS,
        calculate_simple_profession_ratings
    )
    from ..core.rating_history import calculate_rating_deltas_from_history
except ImportError:
    # Fall back to absolute imports for standalone execution
    from gw2_leaderboard.core.glicko_rating_system import (
        PROFESSION_METRICS,
        calculate_simple_profession_ratings
    )
    from gw2_leaderboard.core.rating_history import calculate_rating_deltas_from_history

# Import data processing functions
try:
    from .data_processing import (
        get_glicko_leaderboard_data,
        get_glicko_leaderboard_data_with_sql_filter,
        get_new_high_scores_data,
        get_high_scores_data,
        get_most_played_professions_data,
        generate_player_summaries
    )
except ImportError:
    # Fall back to absolute imports for standalone execution
    from data_processing import (
        get_glicko_leaderboard_data,
        get_glicko_leaderboard_data_with_sql_filter,
        get_new_high_scores_data,
        get_high_scores_data,
        get_most_played_professions_data,
        generate_player_summaries
    )

# Optional guild manager import
try:
    from guild_manager import GuildManager
    GUILD_MANAGER_AVAILABLE = True
except ImportError:
    GUILD_MANAGER_AVAILABLE = False
    GuildManager = None


class ProgressManager:
    """Manages and displays progress for multiple concurrent tasks without flickering."""
    def __init__(self):
        self.progress_data = {}  # Stores {worker_id: {"current": int, "total": int, "timestamp": str, "status": str}}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.bar_length = 40
        self.lines_rendered = 0

    def start(self):
        print("[ProgressManager] Starting...")
        # Disable render loop for now to reduce complexity
        # self.thread = threading.Thread(target=self._render_loop)
        # self.thread.daemon = True
        # self.thread.start()
        print("[ProgressManager] Started.")

    def stop(self):
        print("[ProgressManager] Stopping...")
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join()
        print("[ProgressManager] Stopped.")

    def update_progress(self, worker_id: str, current: int, total: int, timestamp: str):
        with self.lock:
            self.progress_data[worker_id] = {
                "current": current,
                "total": total,
                "timestamp": timestamp,
                "status": "RUNNING"
            }
            # Print progress at 25%, 50%, 75% intervals to reduce noise
            percent = current / total if total > 0 else 0
            if percent in [0.25, 0.5, 0.75] or current == total:
                print(f"  {worker_id}: {current}/{total} ({percent:.0%}) - {timestamp}")

    def complete_worker(self, worker_id: str):
        print(f"[ProgressManager] Completing {worker_id}")
        with self.lock:
            if worker_id in self.progress_data:
                self.progress_data[worker_id]["status"] = "DONE"
                self.progress_data[worker_id]["current"] = self.progress_data[worker_id]["total"]
            # Let the render loop handle the printing
            # self._render()

    def _render_loop(self):
        print("[ProgressManager] Render loop started.")
        while not self.stop_event.is_set():
            self._render()
            time.sleep(0.5)  # Slower updates to reduce flicker
        print("[ProgressManager] Render loop stopped.")

    def _render(self):
        with self.lock:
            # Move cursor to the beginning of the rendered area
            if self.lines_rendered > 0:
                sys.stdout.write(f"\033[{self.lines_rendered}A") # Move cursor up N lines
            
            current_lines = 0
            # Sort workers by ID for consistent display order
            sorted_workers = sorted(self.progress_data.items())
            
            for worker_id, data in sorted_workers:
                current = data["current"]
                total = data["total"]
                timestamp = data["timestamp"]
                status = data["status"]

                percent = current / total if total > 0 else 0
                filled_length = int(self.bar_length * percent)
                bar = '█' * filled_length + '-' * (self.bar_length - filled_length)

                status_str = f"[{status}]"
                line = f'{worker_id:<10} |{bar}| {current}/{total} ({timestamp}) {status_str}'
                sys.stdout.write(f'{line}\033[K\n') # \033[K clears to end of line
                current_lines += 1
            
            # Clear any leftover lines if the number of workers decreases
            if current_lines < self.lines_rendered:
                sys.stdout.write(f"\033[{self.lines_rendered - current_lines}B") # Move cursor down
                sys.stdout.write("\033[J") # Clear from cursor to end of screen
                sys.stdout.write(f"\033[{self.lines_rendered - current_lines}A") # Move cursor back up

            self.lines_rendered = current_lines
            sys.stdout.flush()

    def _get_terminal_size(self):
        try:
            return os.get_terminal_size()
        except OSError:
            return os.terminal_size((80, 24)) # Default if not in a TTY


def generate_all_leaderboard_data(db_path: str, date_filters: List[str], guild_enabled: bool = False, guild_name: str = "", guild_tag: str = "") -> Dict[str, Any]:
    """Generate all leaderboard data with parallel processing."""
    print("Generating all leaderboard data...")
    
    # Create a progress manager
    progress_manager = ProgressManager()
    progress_manager.start()
    
    all_data = {
        "generated_at": datetime.now().isoformat(),
        "guild_enabled": guild_enabled,
        "guild_name": guild_name,
        "guild_tag": guild_tag,
        "date_filters": {}
    }
    
    try:
        # ULTRA-FAST MODE: Generate all data from single database with SQL filtering
        print("  Ultra-fast mode: Single database with SQL filtering...")
        
        # Generate data for each date filter sequentially but with internal parallelism
        for date_filter in date_filters:
            print(f"  Processing {date_filter}...")
            try:
                filter_data = generate_data_for_filter_fast(db_path, date_filter, guild_enabled)
                all_data["date_filters"][date_filter] = filter_data
                progress_manager.complete_worker(date_filter)
                print(f"  ✅ Completed {date_filter}")
            except Exception as e:
                print(f"  ❌ Failed {date_filter}: {e}")
                all_data["date_filters"][date_filter] = {
                    "individual_metrics": {},
                    "profession_leaderboards": {},
                    "high_scores": {},
                    "player_stats": {}
                }
        
        print("  🚀 Ultra-fast generation complete!")
    
    finally:
        progress_manager.stop()
    
    print("✅ All leaderboard data generation complete")
    return all_data


def calculate_simple_profession_ratings_fast_filter(db_path: str, profession: str, date_filter: str, guild_filter: bool = False):
    """Fast profession ratings with date filtering using existing data."""
    try:
        # Get the overall profession ratings first
        overall_data = calculate_simple_profession_ratings(
            db_path, profession, 
            date_filter=None,
            guild_filter=guild_filter
        )
        
        if not overall_data:
            return []
        
        # Now filter by players who have recent activity
        days = int(date_filter.rstrip('d'))
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get accounts with recent activity
        cursor.execute('''
            SELECT DISTINCT account_name 
            FROM player_performances 
            WHERE parsed_date >= date('now', '-{} days')
        '''.format(days))
        
        recent_accounts = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        # Filter the overall data to only include recently active players
        filtered_data = []
        for player_tuple in overall_data:
            account_name = player_tuple[0]  # First element is account name
            if account_name in recent_accounts:
                filtered_data.append(player_tuple)
        
        return filtered_data
        
    except Exception as e:
        print(f"Error in fast profession filtering: {e}")
        # Fall back to overall data if filtering fails
        return calculate_simple_profession_ratings(
            db_path, profession, 
            date_filter=None,
            guild_filter=guild_filter
        )

def _generate_filtered_db(db_path: str, date_filter: str) -> str:
    """Generate a filtered database for a specific date filter."""
    try:
        from ..core.glicko_rating_system import calculate_date_filtered_ratings
        return calculate_date_filtered_ratings(db_path, date_filter, guild_filter=False)
    except Exception as e:
        print(f"Error generating filtered DB for {date_filter}: {e}")
        return db_path

def _process_single_metric_fast(args):
    """Process a single metric using SQL-level date filtering for speed."""
    db_path, metric, date_filter, guild_enabled = args
    try:
        print(f"    Processing {metric}...")
        # Use direct SQL approach instead of expensive database copying
        data = get_glicko_leaderboard_data_with_sql_filter(db_path, metric, date_filter, limit=500, show_deltas=True)
        return metric, data
    except Exception as e:
        print(f"    Error processing {metric}: {e}")
        return metric, []

def _process_single_metric(args):
    """Process a single metric for parallel execution."""
    db_path, metric, date_filter, guild_enabled = args
    try:
        print(f"    Processing {metric}...")
        # Since we pre-filter databases, always use None for date_filter to avoid circular calls
        data = get_glicko_leaderboard_data(db_path, metric, limit=500, date_filter=None, show_deltas=True)
        return metric, data
    except Exception as e:
        print(f"    Error processing {metric}: {e}")
        return metric, []


def _process_single_profession_fast(args):
    """Process a single profession using SQL-level date filtering for speed."""
    db_path, profession, date_filter, guild_enabled = args
    
    try:
        print(f"    Processing profession {profession}...")
        
        # Get profession configuration
        prof_config = PROFESSION_METRICS.get(profession, {
            'metrics': ['DPS'],
            'weights': [1.0],
            'key_stats_format': 'DPS: {}'
        })
        
        # Use fast date filtering for profession ratings
        # This filters by players who were active in the specified time period
        # For fast processing, use existing ratings but filter by recent activity
        if date_filter and date_filter != "overall":
            profession_data = calculate_simple_profession_ratings_fast_filter(
                db_path, profession, date_filter, guild_enabled
            )
        else:
            profession_data = calculate_simple_profession_ratings(
                db_path, profession, 
                date_filter=None,
                guild_filter=guild_enabled
            )
        
        if not profession_data:
            return profession, None
        
        # ... rest of the processing (guild membership, rating deltas, structured data)
        # [Copy the rest from the original function]
        
        # Check if guild_members table exists for guild membership info
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
        guild_table_exists = cursor.fetchone() is not None
        conn.close()
        
        # Add guild membership info if available
        if guild_table_exists:
            for i, player_tuple in enumerate(profession_data):
                account_name = player_tuple[0]
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM guild_members WHERE account_name = ?", (account_name,))
                is_guild_member = cursor.fetchone() is not None
                conn.close()
                
                # Convert to list, add guild membership, convert back to tuple
                player_list = list(player_tuple)
                player_list.append(is_guild_member)
                profession_data[i] = tuple(player_list)
        else:
            # Add False for guild membership if table doesn't exist
            for i, player_tuple in enumerate(profession_data):
                player_list = list(player_tuple)
                player_list.append(False)
                profession_data[i] = tuple(player_list)
        
        # Add rating deltas (simplified for speed)
        for i, player_tuple in enumerate(profession_data):
            player_list = list(player_tuple)
            player_list.append(0.0)  # TODO: Implement fast rating delta calculation
            profession_data[i] = tuple(player_list)
        
        # Convert raw array data to structured object expected by JavaScript
        structured_data = {
            'metrics': prof_config['metrics'],
            'weights': prof_config['weights'],
            'key_stats_format': prof_config.get('key_stats_format', 'Stats: {}'),
            'players': []
        }
        
        # Convert tuple data to objects for JavaScript
        for player_tuple in profession_data:
            apm_total = player_tuple[6] if len(player_tuple) > 6 else 0.0
            apm_no_auto = player_tuple[7] if len(player_tuple) > 7 else 0.0
            
            player_obj = {
                'account_name': player_tuple[0],
                'composite_score': player_tuple[1],
                'games_played': player_tuple[2],
                'average_rank_percent': player_tuple[3],
                'glicko_rating': player_tuple[4],
                'key_stats': player_tuple[5],
                'apm_total': apm_total,
                'apm_no_auto': apm_no_auto,
                'apm': f"{apm_total:.1f}/{apm_no_auto:.1f}" if apm_total > 0 or apm_no_auto > 0 else "0.0/0.0",
                'is_guild_member': player_tuple[8] if len(player_tuple) > 8 else False,
                'rating_delta': player_tuple[9] if len(player_tuple) > 9 else 0.0
            }
            structured_data['players'].append(player_obj)
        
        return profession, structured_data
        
    except Exception as e:
        print(f"      Error processing profession {profession}: {e}")
        import traceback
        traceback.print_exc()
        return profession, None

def _process_single_profession(args):
    """Process a single profession for parallel execution."""
    db_path, profession, date_filter, guild_enabled = args
    
    try:
        print(f"    Processing profession {profession}...")
        
        # Get profession configuration
        prof_config = PROFESSION_METRICS.get(profession, {
            'metrics': ['DPS'],
            'weights': [1.0],
            'key_stats_format': 'DPS: {}'
        })
        
        # Calculate profession ratings using simple method
        # Since we pre-filter databases, always use None for date_filter to avoid circular calls
        profession_data = calculate_simple_profession_ratings(
            db_path, profession, 
            date_filter=None,
            guild_filter=guild_enabled
        )
        
        if not profession_data:
            return profession, None
        
        # Check if guild_members table exists for guild membership info
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
        guild_table_exists = cursor.fetchone() is not None
        conn.close()
        
        # Add guild membership info if available
        if guild_table_exists and guild_enabled:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            for player in profession_data:
                cursor.execute(
                    "SELECT account_name FROM guild_members WHERE account_name = ?",
                    (player[0],)
                )
                player_list = list(player)
                player_list.append(cursor.fetchone() is not None)
                profession_data[profession_data.index(player)] = tuple(player_list)
            
            conn.close()
        else:
            # Set all players as non-guild members
            for player in profession_data:
                player_list = list(player)
                player_list.append(False)
                profession_data[profession_data.index(player)] = tuple(player_list)
        
        # Add rating deltas
        try:
            # Get all rating deltas for this profession
            all_deltas = calculate_rating_deltas_from_history(db_path, "Overall")
            for player in profession_data:
                try:
                    delta_key = (player[0], profession, "Overall")
                    player_list = list(player)
                    player_list.append(all_deltas.get(delta_key, 0.0))
                    profession_data[profession_data.index(player)] = tuple(player_list)
                except Exception as e:
                    print(f"      Warning: Could not get rating delta for {player[0]}: {e}")
                    player_list = list(player)
                    player_list.append(0.0)
                    profession_data[profession_data.index(player)] = tuple(player_list)
        except Exception as e:
            print(f"      Warning: Could not get rating deltas for {profession}: {e}")
            for player in profession_data:
                player_list = list(player)
                player_list.append(0.0)
                profession_data[profession_data.index(player)] = tuple(player_list)
        
        # Convert raw array data to structured object expected by JavaScript
        structured_data = {
            'metrics': prof_config['metrics'],
            'weights': prof_config['weights'],
            'key_stats_format': prof_config.get('key_stats_format', 'Stats: {}'),
            'players': []
        }
        
        # Convert tuple data to objects for JavaScript
        for player_tuple in profession_data:
            apm_total = player_tuple[6] if len(player_tuple) > 6 else 0.0
            apm_no_auto = player_tuple[7] if len(player_tuple) > 7 else 0.0
            
            player_obj = {
                'account_name': player_tuple[0],
                'composite_score': player_tuple[1],
                'games_played': player_tuple[2],
                'average_rank_percent': player_tuple[3],
                'glicko_rating': player_tuple[4],
                'key_stats': player_tuple[5],
                'apm_total': apm_total,
                'apm_no_auto': apm_no_auto,
                'apm': f"{apm_total:.1f}/{apm_no_auto:.1f}" if apm_total > 0 or apm_no_auto > 0 else "0.0/0.0",
                'is_guild_member': player_tuple[8] if len(player_tuple) > 8 else False,
                'rating_delta': player_tuple[9] if len(player_tuple) > 9 else 0.0
            }
            structured_data['players'].append(player_obj)
        
        return profession, structured_data
        
    except Exception as e:
        import traceback
        print(f"    Error processing profession {profession}: {e}")
        traceback.print_exc()
        return profession, None


def generate_data_for_filter_fast(db_path: str, date_filter: str, guild_enabled: bool = False) -> Dict[str, Any]:
    """Generate leaderboard data using SQL-level date filtering for maximum speed."""
    print(f"Generating data for {date_filter}...")
    
    filter_data = {
        "individual_metrics": {},
        "profession_leaderboards": {},
        "high_scores": {},
        "player_stats": {}
    }
    
    # Individual metrics - use reduced parallelism to avoid contention
    print(f"  Processing individual metrics for {date_filter}...")
    individual_metrics = [
        'DPS', 'Healing', 'Barrier', 'Cleanses', 'Strips', 
        'Stability', 'Resistance', 'Might', 'Protection', 
        'Downs', 'Burst Consistency', 'Distance to Tag'
    ]
    
    # Process metrics sequentially to eliminate database contention
    for metric in individual_metrics:
        print(f"    Processing {metric}...")
        try:
            data = get_glicko_leaderboard_data_with_sql_filter(db_path, metric, date_filter, limit=500, show_deltas=True)
            filter_data["individual_metrics"][metric] = data
        except Exception as e:
            print(f"    Error processing {metric}: {e}")
            filter_data["individual_metrics"][metric] = []
    
    # Profession leaderboards - use reduced parallelism
    print(f"  Processing profession leaderboards for {date_filter}...")
    professions = list(PROFESSION_METRICS.keys()) + ["Condi Firebrand", "Support Spb"]
    
    # Process professions sequentially to eliminate database contention
    for profession in professions:
        args = (db_path, profession, date_filter, guild_enabled)
        profession_name, data = _process_single_profession_fast(args)
        if data is not None:
            filter_data["profession_leaderboards"][profession_name] = data
    
    # High scores - no date filtering needed, use overall data
    print(f"  Processing high scores for {date_filter}...")
    try:
        high_scores_data = get_new_high_scores_data(db_path, limit=100)
        if not high_scores_data:
            high_scores_data = get_high_scores_data(db_path, limit=100)
        filter_data["high_scores"] = high_scores_data
    except Exception as e:
        print(f"      Warning: Could not get high scores: {e}")
        filter_data["high_scores"] = {}
    
    # Player stats - use overall data
    print(f"  Processing player stats for {date_filter}...")
    try:
        player_stats_data = get_most_played_professions_data(db_path, limit=100)
        filter_data["player_stats"] = player_stats_data
    except Exception as e:
        print(f"      Warning: Could not get player stats: {e}")
        filter_data["player_stats"] = {}
    
    print(f"  ✅ Completed data generation for {date_filter}")
    return filter_data

def generate_data_for_filter_with_db(db_path: str, date_filter: str, guild_enabled: bool = False) -> Dict[str, Any]:
    """Generate all leaderboard data for a single date filter using pre-filtered database."""
    return generate_data_for_filter(db_path, date_filter, guild_enabled)

def generate_data_for_filter(db_path: str, date_filter: str, guild_enabled: bool = False) -> Dict[str, Any]:
    """Generate all leaderboard data for a single date filter."""
    print(f"Generating data for {date_filter}...")
    
    filter_data = {
        "individual_metrics": {},
        "profession_leaderboards": {},
        "high_scores": {},
        "player_stats": {}
    }
    
    # Individual metrics - process in parallel
    print(f"  Processing individual metrics for {date_filter}...")
    individual_metrics = [
        'DPS', 'Healing', 'Barrier', 'Cleanses', 'Strips', 
        'Stability', 'Resistance', 'Might', 'Protection', 
        'Downs', 'Burst Consistency', 'Distance to Tag'
    ]
    
    # Process metrics in parallel with increased workers for your powerful CPU
    with ThreadPoolExecutor(max_workers=16) as executor:
        metric_args = [(db_path, metric, date_filter, guild_enabled) for metric in individual_metrics]
        results = list(executor.map(_process_single_metric, metric_args))
        
        for metric, data in results:
            filter_data["individual_metrics"][metric] = data
    
    # Profession leaderboards - process in parallel
    print(f"  Processing profession leaderboards for {date_filter}...")
    professions = list(PROFESSION_METRICS.keys()) + ["Condi Firebrand", "Support Spb"]
    
    with ThreadPoolExecutor(max_workers=12) as executor:
        profession_args = [(db_path, profession, date_filter, guild_enabled) for profession in professions]
        results = list(executor.map(_process_single_profession, profession_args))
        
        for profession, data in results:
            if data is not None:
                filter_data["profession_leaderboards"][profession] = data
    
    # High scores
    print(f"  Processing high scores for {date_filter}...")
    try:
        # Try new high_scores table first
        high_scores_data = get_new_high_scores_data(db_path, limit=100)
        if not high_scores_data:
            # Fall back to legacy method
            high_scores_data = get_high_scores_data(db_path, limit=100)
        filter_data["high_scores"] = high_scores_data
    except Exception as e:
        import traceback
        print(f"    Error getting high scores: {e}")
        traceback.print_exc()
        filter_data["high_scores"] = {}
    
    # Player stats
    print(f"  Processing player stats for {date_filter}...")
    try:
        most_played = get_most_played_professions_data(db_path, limit=500)
        filter_data["player_stats"] = {
            "Most Played Professions": most_played
        }
    except Exception as e:
        print(f"    Error getting player stats: {e}")
        filter_data["player_stats"] = {"Most Played Professions": []}
    
    print(f"  ✅ Completed data generation for {date_filter}")
    return filter_data