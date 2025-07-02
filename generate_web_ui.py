#!/usr/bin/env python3
"""
Generate static web UI for GW2 WvW Leaderboards.
Creates HTML/CSS/JS interface that can be uploaded to GitHub Pages.
"""

import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

# Add current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from glicko_rating_system import (
    PROFESSION_METRICS,
    recalculate_all_glicko_ratings,
    recalculate_profession_ratings,
    calculate_date_filtered_ratings
)

# Optional guild manager import
try:
    from guild_manager import GuildManager
    GUILD_MANAGER_AVAILABLE = True
except ImportError:
    GUILD_MANAGER_AVAILABLE = False
    GuildManager = None

# Optional player summary import
try:
    from player_summary import PlayerSummaryGenerator
    PLAYER_SUMMARY_AVAILABLE = True
except ImportError:
    PLAYER_SUMMARY_AVAILABLE = False
    PlayerSummaryGenerator = None


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






def get_glicko_leaderboard_data(db_path: str, metric_category: str = None, limit: int = 100, date_filter: str = None):
    """Extract leaderboard data from database with guild membership info."""
    if date_filter:
        # For date filtering, we need to recalculate ratings on filtered data
        return get_filtered_leaderboard_data(db_path, metric_category, limit, date_filter)
    
    # No date filter - use existing glicko_ratings table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if guild_members table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    
    # Debug info for guild membership (only in non-main database paths to avoid spam)
    if guild_table_exists and '/tmp' in db_path:
        cursor.execute("SELECT COUNT(*) FROM guild_members")
        guild_count = cursor.fetchone()[0]
        print(f"[DEBUG] get_glicko_leaderboard_data: guild_members table found with {guild_count} members in {db_path}")
    
    if metric_category and metric_category != "Overall":
        # Specific metric category with guild membership info
        if guild_table_exists:
            cursor.execute('''
                SELECT g.account_name, g.profession, g.composite_score, g.rating, g.games_played, 
                       g.average_rank, g.average_stat_value,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM glicko_ratings g
                LEFT JOIN guild_members gm ON g.account_name = gm.account_name
                WHERE g.metric_category = ?
                ORDER BY g.composite_score DESC
                LIMIT ?
            ''', (metric_category, limit))
        else:
            cursor.execute('''
                SELECT account_name, profession, composite_score, rating, games_played, 
                       average_rank, average_stat_value, 0 as is_guild_member
                FROM glicko_ratings 
                WHERE metric_category = ?
                ORDER BY composite_score DESC
                LIMIT ?
            ''', (metric_category, limit))
    else:
        # Overall leaderboard with guild membership info
        if guild_table_exists:
            cursor.execute('''
                SELECT g.account_name, g.profession, 
                       AVG(g.composite_score) as avg_composite,
                       AVG(g.rating) as avg_rating,
                       SUM(g.games_played) as total_games,
                       AVG(g.average_rank) as avg_rank,
                       AVG(g.average_stat_value) as avg_stat,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM glicko_ratings g
                LEFT JOIN guild_members gm ON g.account_name = gm.account_name
                GROUP BY g.account_name, g.profession
                ORDER BY avg_composite DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT account_name, profession, 
                       AVG(composite_score) as avg_composite,
                       AVG(rating) as avg_rating,
                       SUM(games_played) as total_games,
                       AVG(average_rank) as avg_rank,
                       AVG(average_stat_value) as avg_stat,
                       0 as is_guild_member
                FROM glicko_ratings
                GROUP BY account_name, profession
                ORDER BY avg_composite DESC
                LIMIT ?
            ''', (limit,))
    
    results = cursor.fetchall()
    conn.close()
    return results


def get_filtered_leaderboard_data(db_path: str, metric_category: str, limit: int, date_filter: str):
    """Get leaderboard data filtered by date - uses same method as CLI."""
    from glicko_rating_system import calculate_date_filtered_ratings
    
    # Use the same method as the CLI for date filtering (all players)
    working_db_path = calculate_date_filtered_ratings(db_path, date_filter, guild_filter=False)
    
    # Now get the results from the filtered database with guild membership info
    conn = sqlite3.connect(working_db_path)
    cursor = conn.cursor()
    
    # Check if guild_members table exists in original database
    original_conn = sqlite3.connect(db_path)
    original_cursor = original_conn.cursor()
    original_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = original_cursor.fetchone() is not None
    
    if guild_table_exists:
        # Copy guild_members table to the temporary database for the JOIN
        original_cursor.execute("SELECT * FROM guild_members")
        guild_data = original_cursor.fetchall()
        
        # Create guild_members table in temp database
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_members (
                account_name TEXT PRIMARY KEY,
                guild_rank TEXT,
                joined_date TEXT,
                wvw_member INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert guild data
        cursor.executemany('''
            INSERT OR REPLACE INTO guild_members 
            (account_name, guild_rank, joined_date, wvw_member, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', guild_data)
    
    original_conn.close()
    
    if metric_category and metric_category != "Overall":
        # Specific metric category with guild membership info
        if guild_table_exists:
            cursor.execute('''
                SELECT g.account_name, g.profession, g.composite_score, g.rating, g.games_played, 
                       g.average_rank, g.average_stat_value,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM glicko_ratings g
                LEFT JOIN guild_members gm ON g.account_name = gm.account_name
                WHERE g.metric_category = ?
                ORDER BY g.composite_score DESC
                LIMIT ?
            ''', (metric_category, limit))
        else:
            cursor.execute('''
                SELECT account_name, profession, composite_score, rating, games_played, 
                       average_rank, average_stat_value, 0 as is_guild_member
                FROM glicko_ratings 
                WHERE metric_category = ?
                ORDER BY composite_score DESC
                LIMIT ?
            ''', (metric_category, limit))
    else:
        # Overall leaderboard with guild membership info
        if guild_table_exists:
            cursor.execute('''
                SELECT g.account_name, g.profession, 
                       AVG(g.composite_score) as avg_composite,
                       AVG(g.rating) as avg_rating,
                       SUM(g.games_played) as total_games,
                       AVG(g.average_rank) as avg_rank,
                       AVG(g.average_stat_value) as avg_stat,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM glicko_ratings g
                LEFT JOIN guild_members gm ON g.account_name = gm.account_name
                GROUP BY g.account_name, g.profession
                ORDER BY avg_composite DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT account_name, profession, 
                       AVG(composite_score) as avg_composite,
                       AVG(rating) as avg_rating,
                       SUM(games_played) as total_games,
                       AVG(average_rank) as avg_rank,
                       AVG(average_stat_value) as avg_stat,
                       0 as is_guild_member
                FROM glicko_ratings
                GROUP BY account_name, profession
                ORDER BY avg_composite DESC
                LIMIT ?
            ''', (limit,))
    
    results = cursor.fetchall()
    conn.close()
    
    # Clean up temporary database if created
    if working_db_path != db_path:
        import os
        try:
            os.remove(working_db_path)
        except OSError:
            pass
    
    return results


def get_new_high_scores_data(db_path: str, limit: int = 100, date_filter: str = None):
    """Get high scores data from the new high_scores table."""
    from glicko_rating_system import build_date_filter_clause
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if guild_members table exists for guild membership info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    
    # Build date filter clause
    date_clause, date_params = build_date_filter_clause(date_filter)
    
    high_scores_data = {}
    
    # Target metrics to extract
    target_metrics = {
        'highest_outgoing_skill_damage': 'Highest Outgoing Skill Damage',
        'highest_incoming_skill_damage': 'Highest Incoming Skill Damage',
        'highest_single_fight_dps': 'Highest Single Fight DPS'
    }
    
    for metric_key, metric_name in target_metrics.items():
        if guild_table_exists:
            # Query with guild membership info
            query = f'''
                SELECT hs.player_account, hs.player_name, hs.profession, hs.skill_name, 
                       hs.score_value, hs.timestamp, hs.fight_number,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM high_scores hs
                LEFT JOIN guild_members gm ON hs.player_account = gm.account_name
                WHERE hs.metric_type = ? {date_clause}
                ORDER BY hs.score_value DESC
                LIMIT ?
            '''
            params = [metric_key] + date_params + [limit]
            cursor.execute(query, params)
        else:
            # Query without guild membership info
            query = f'''
                SELECT player_account, player_name, profession, skill_name, 
                       score_value, timestamp, fight_number, 0 as is_guild_member
                FROM high_scores
                WHERE metric_type = ? {date_clause}
                ORDER BY score_value DESC
                LIMIT ?
            '''
            params = [metric_key] + date_params + [limit]
            cursor.execute(query, params)
        
        results = cursor.fetchall()
        high_scores_data[metric_name] = [
            {
                "rank": i + 1,
                "account_name": account,
                "player_name": player_name,
                "profession": profession,
                "skill_name": skill_name,
                "score_value": score_value,
                "timestamp": timestamp,
                "fight_number": fight_number,
                "is_guild_member": bool(is_guild_member)
            }
            for i, (account, player_name, profession, skill_name, score_value, timestamp, fight_number, is_guild_member) in enumerate(results)
        ]
    
    conn.close()
    return high_scores_data


def get_high_scores_data(db_path: str, limit: int = 100, date_filter: str = None):
    """Get top burst damage records for High Scores section (non-Glicko based)."""
    from glicko_rating_system import build_date_filter_clause
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if guild_members table exists for guild membership info
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    
    # Build date filter clause
    date_clause, date_params = build_date_filter_clause(date_filter)
    
    if guild_table_exists:
        # Query with guild membership info
        query = f'''
            SELECT p.account_name, p.profession, p.burst_damage_1s, p.timestamp,
                   CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
            FROM player_performances p
            LEFT JOIN guild_members gm ON p.account_name = gm.account_name
            WHERE p.burst_damage_1s > 0 {date_clause}
            ORDER BY p.burst_damage_1s DESC
            LIMIT ?
        '''
        params = date_params + [limit]
        cursor.execute(query, params)
    else:
        # Query without guild membership info
        query = f'''
            SELECT account_name, profession, burst_damage_1s, timestamp, 0 as is_guild_member
            FROM player_performances
            WHERE burst_damage_1s > 0 {date_clause}
            ORDER BY burst_damage_1s DESC
            LIMIT ?
        '''
        params = date_params + [limit]
        cursor.execute(query, params)
    
    results = cursor.fetchall()
    conn.close()
    return results


def generate_player_summaries_for_filter(db_path: str, output_dir: Path, date_filter: str, active_players: List[tuple]) -> List[str]:
    """Generate player summaries for a specific date filter."""
    filter_suffix = f"_{date_filter}" if date_filter != "overall" else ""
    filter_dir = output_dir / "players" / date_filter if date_filter != "overall" else output_dir / "players"
    filter_dir.mkdir(parents=True, exist_ok=True)
    
    generated_files = []
    generator = PlayerSummaryGenerator(db_path, date_filter if date_filter != "overall" else None)
    
    try:
        for account_name, session_count in active_players:
            try:
                # Generate summary
                summary = generator.generate_summary(account_name)
                if summary:
                    # Convert to dict for JSON serialization
                    def to_dict(obj):
                        if hasattr(obj, '__dict__'):
                            return {k: to_dict(v) for k, v in obj.__dict__.items()}
                        elif isinstance(obj, list):
                            return [to_dict(item) for item in obj]
                        elif isinstance(obj, dict):
                            return {k: to_dict(v) for k, v in obj.items()}
                        else:
                            return obj
                    
                    summary_dict = to_dict(summary)
                    
                    # Create safe filename
                    safe_name = account_name.replace('.', '_').replace(' ', '_')
                    filename = f"{safe_name}{filter_suffix}.json"
                    filepath = filter_dir / filename
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(summary_dict, f, indent=2)
                    
                    generated_files.append(account_name)
                
            except Exception as e:
                print(f"  Warning: Failed to generate {date_filter} summary for {account_name}: {e}")
                continue
    
    finally:
        generator.close()
    
    return generated_files


def generate_player_summaries(db_path: str, output_dir: Path) -> List[str]:
    """Generate player summary JSON files for all active players with date filtering."""
    if not PLAYER_SUMMARY_AVAILABLE:
        print("Player summary generation not available (missing player_summary.py)")
        return []
    
    print("Generating player summaries...")
    
    # Get top 150 active players by session count (minimum 3 sessions)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT account_name, COUNT(DISTINCT timestamp) as sessions
        FROM player_performances 
        GROUP BY account_name
        HAVING sessions >= 3
        ORDER BY sessions DESC
        LIMIT 150
    """)
    
    active_players = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(active_players)} top active players (3+ sessions, limited to 150)")
    
    # Create players directory
    players_dir = output_dir / "players"
    players_dir.mkdir(exist_ok=True)
    
    # Date filters to generate
    date_filters = ['overall', '30d', '90d', '180d']
    
    # Generate summaries for each date filter using multithreading
    all_generated_files = {}
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit tasks for each date filter
        future_to_filter = {
            executor.submit(generate_player_summaries_for_filter, db_path, output_dir, date_filter, active_players): date_filter
            for date_filter in date_filters
        }
        
        # Process results as they complete
        for future in as_completed(future_to_filter):
            date_filter = future_to_filter[future]
            try:
                generated_files = future.result()
                all_generated_files[date_filter] = generated_files
                print(f"✅ Generated {len(generated_files)} {date_filter} player summaries")
            except Exception as e:
                print(f"❌ Failed to generate {date_filter} summaries: {e}")
                all_generated_files[date_filter] = []
    
    # Generate player index for all filters
    player_index = {
        "generated_at": datetime.now().isoformat(),
        "date_filters": all_generated_files,
        "total_players": len(all_generated_files.get('overall', []))
    }
    
    with open(players_dir / "index.json", 'w', encoding='utf-8') as f:
        json.dump(player_index, f, indent=2)
    
    print(f"✅ Generated player summaries for {len(date_filters)} date filters")
    return all_generated_files.get('overall', [])


def generate_all_leaderboard_data(db_path: str, max_workers: int = 4) -> Dict[str, Any]:
    """Generate all leaderboard data in JSON format. 
    
    Note: Due to Python GIL limitations and SQLite locking, CPU-intensive date filtering
    operations may execute sequentially despite using threads. The overall filter is
    processed first for immediate user feedback.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    conn.close()

    guild_name = "Guild"
    guild_tag = "UNK"
    if GUILD_MANAGER_AVAILABLE and guild_table_exists:
        try:
            guild_manager = GuildManager()
            guild_name = guild_manager.guild_config.get("guild_name", "Guild")
            guild_tag = guild_manager.guild_config.get("guild_tag", "UNK")
        except Exception as e:
            print(f"Could not load guild config, using defaults: {e}")

    data = {
        "generated_at": datetime.now().isoformat(),
        "guild_enabled": guild_table_exists,
        "guild_name": guild_name,
        "guild_tag": guild_tag,
        "date_filters": {}
    }

    date_filters = {
        "overall": None,
        "30d": "30d",
        "90d": "90d",
        "180d": "180d"
    }

    progress_manager = ProgressManager()
    progress_manager.start()

    try:
        # Process overall first (fast), then date filters (slow) for better UX
        print(f"Processing {len(date_filters)} filters (overall first, then date-filtered)...")
        
        # Process overall filter first if it exists
        if "overall" in date_filters:
            print("🚀 Processing 'overall' filter (fast)...")
            try:
                filter_data = generate_data_for_filter(db_path, None, progress_manager, "overall")
                data["date_filters"]["overall"] = filter_data
                print("✅ Overall filter completed")
            except Exception as exc:
                print(f'Overall filter failed: {exc}')
                import traceback
                traceback.print_exc()
        
        # Process date filters with ProcessPoolExecutor for true CPU parallelism
        date_only_filters = {k: v for k, v in date_filters.items() if k != "overall"}
        if date_only_filters:
            print(f"🔄 Processing {len(date_only_filters)} date filters with ProcessPoolExecutor...")
            print("   📊 Each filter requires ~30-60 seconds for temporary database creation and rating calculations")
            print(f"   ⏱️  Estimated total time: ~{len(date_only_filters) * 45} seconds")
            print("   🚀 Using process-based parallelism to bypass Python GIL limitations")
            
            with ProcessPoolExecutor(max_workers=min(len(date_only_filters), max_workers)) as executor:
                print(f"🚀 Starting {len(date_only_filters)} processes for date filters...")
                
                # Submit all date filter tasks
                future_to_filter = {
                    executor.submit(generate_data_for_filter, db_path, filter_value, None, filter_name): filter_name
                    for filter_name, filter_value in date_only_filters.items()
                }
                
                print("⏳ Processing date filters...")
                print("   💡 Using separate processes for true CPU parallelism during intensive calculations")
                
                completed = 0
                for future in as_completed(future_to_filter):
                    filter_name = future_to_filter[future]
                    try:
                        filter_data = future.result()
                        data["date_filters"][filter_name] = filter_data
                        completed += 1
                        print(f"✅ {filter_name} completed ({completed}/{len(date_only_filters)})")
                    except Exception as exc:
                        print(f'{filter_name} failed: {exc}')
                        import traceback
                        traceback.print_exc()
        
        print("🏁 All filters completed")
    finally:
        print("Stopping progress manager...")
        progress_manager.stop()
        print("Progress manager stopped")
    

    return data


def _process_single_metric(db_path: str, category: str, filter_value: str, worker_id: str) -> tuple:
    """Process a single metric category and return results."""
    import threading
    import time
    from datetime import datetime
    thread_name = threading.current_thread().name
    start_time = time.time()
    timestamp = datetime.now().strftime('%H:%M:%S')
    try:
        print(f"[{worker_id}:{thread_name}] 🚀 {timestamp} STARTING metric: {category}")
        results = get_glicko_leaderboard_data(db_path, category, limit=100, date_filter=filter_value)
        end_time = time.time()
        end_timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{worker_id}:{thread_name}] ✅ {end_timestamp} COMPLETED metric: {category} ({len(results)} results) in {end_time - start_time:.2f}s")
        return category, results
    except Exception as e:
        end_time = time.time()
        end_timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{worker_id}:{thread_name}] ❌ {end_timestamp} ERROR processing {category} in {end_time - start_time:.2f}s: {e}")
        return category, []


def _process_single_profession(db_path: str, profession: str, filter_value: str, worker_id: str, progress_callback) -> Dict[str, Any]:
    """Process a single profession leaderboard and return formatted data."""
    import threading
    import time
    from datetime import datetime
    thread_name = threading.current_thread().name
    start_time = time.time()
    timestamp = datetime.now().strftime('%H:%M:%S')
    try:
        print(f"[{worker_id}:{thread_name}] 🚀 {timestamp} STARTING profession: {profession}")
        results = recalculate_profession_ratings(db_path, profession, date_filter=filter_value, guild_filter=False, progress_callback=progress_callback)
        
        if not results:
            end_timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{worker_id}:{thread_name}] ⚠️ {end_timestamp} No results for profession: {profession}")
            return None
            
        prof_config = PROFESSION_METRICS[profession]

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
        guild_table_exists = cursor.fetchone() is not None

        players_with_guild_info = []
        for i, (account, rating, games, avg_rank, composite, stats_breakdown) in enumerate(results[:100]):
            is_guild_member = False
            if guild_table_exists:
                cursor.execute("SELECT 1 FROM guild_members WHERE account_name = ?", (account,))
                is_guild_member = cursor.fetchone() is not None
            
            players_with_guild_info.append({
                "rank": i + 1,
                "account_name": account,
                "composite_score": float(composite),
                "glicko_rating": float(rating),
                "games_played": int(games),
                "average_rank_percent": float(avg_rank) if avg_rank > 0 else None,
                "key_stats": stats_breakdown,
                "is_guild_member": is_guild_member
            })
        
        conn.close()
        
        end_time = time.time()
        end_timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{worker_id}:{thread_name}] ✅ {end_timestamp} COMPLETED profession: {profession} ({len(players_with_guild_info)} players) in {end_time - start_time:.2f}s")
        
        return {
            "metrics": prof_config["metrics"],
            "weights": prof_config["weights"],
            "players": players_with_guild_info
        }
        
    except Exception as e:
        end_time = time.time()
        end_timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{worker_id}:{thread_name}] ❌ {end_timestamp} ERROR processing profession {profession} in {end_time - start_time:.2f}s: {e}")
        return None


def generate_data_for_filter(db_path: str, filter_value: str, progress_manager: ProgressManager, worker_id: str) -> Dict[str, Any]:
    """Generates all leaderboard data for a single date filter."""
    import threading
    import time
    print(f"[{worker_id}] WORKER STARTING on thread {threading.current_thread().name} at {time.time()}")
    print(f"[{worker_id}] Starting worker for filter: {filter_value}")
    filter_name = filter_value if filter_value else "overall"
    
    # Track temporary database path for cleanup
    temp_db_path = None
    
    # Store original database path before it gets overwritten
    original_db_path = db_path

    # Define a local progress callback for this worker
    def worker_progress_callback(current, total, timestamp):
        if progress_manager:
            progress_manager.update_progress(worker_id, current, total, timestamp)
        else:
            # For process-based execution, just print progress
            percent = current / total if total > 0 else 0
            if percent in [0.25, 0.5, 0.75] or current == total:
                print(f"  {worker_id}: {current}/{total} ({percent:.0%}) - {timestamp}")

    try:
        filter_data = {
            "individual_metrics": {},
            "profession_leaderboards": {},
            "overall_leaderboard": [],
            "high_scores": {}
        }

        individual_categories = [
            "DPS", "Healing", "Barrier", "Cleanses", "Strips",
            "Stability", "Resistance", "Might", "Protection", "Downs", "Burst Consistency"
        ]

        # When using a date filter, we need to recalculate ratings. For thread safety,
        # each worker will do this on a temporary, isolated copy of the database.
        print(f"[{worker_id}] 🚀 Worker now preparing database...")
        if not filter_value:
            print(f"[{worker_id}] Using main database for overall filter")
            # For the 'overall' filter, we can use the main pre-calculated ratings.
            # This avoids redundant calculations.
            pass
        else:
            print(f"[{worker_id}] Creating temporary database for date filter: {filter_value} (this may take 30-60 seconds)")
            # For date-filtered views, recalculate ratings in a temporary DB.
            start_time = time.time()
            print(f"[{worker_id}] 🔄 CALLING calculate_date_filtered_ratings at {start_time}")
            working_db_path = calculate_date_filtered_ratings(db_path, filter_value, guild_filter=False, progress_callback=worker_progress_callback)
            temp_db_path = working_db_path  # Store for cleanup
            db_path = working_db_path
            end_time = time.time()
            print(f"[{worker_id}] ✅ RETURNED from calculate_date_filtered_ratings in {end_time - start_time:.2f}s: {working_db_path}")
            
            # Copy guild_members table to temporary database for guild recognition
            print(f"[{worker_id}] Copying guild data to temporary database...")
            original_conn = sqlite3.connect(original_db_path)
            original_cursor = original_conn.cursor()
            original_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
            guild_table_exists = original_cursor.fetchone() is not None
            
            if guild_table_exists:
                # Copy guild_members table to the temporary database for the JOIN
                original_cursor.execute("SELECT * FROM guild_members")
                guild_data = original_cursor.fetchall()
                
                temp_conn = sqlite3.connect(db_path)
                temp_cursor = temp_conn.cursor()
                
                # Create guild_members table in temp database
                temp_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS guild_members (
                        account_name TEXT PRIMARY KEY,
                        guild_rank TEXT,
                        joined_date TEXT,
                        wvw_member INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Insert guild data
                temp_cursor.executemany('''
                    INSERT OR REPLACE INTO guild_members 
                    (account_name, guild_rank, joined_date, wvw_member, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                ''', guild_data)
                
                temp_conn.commit()
                temp_conn.close()
                print(f"[{worker_id}] ✅ Copied {len(guild_data)} guild members to temporary database")
            else:
                print(f"[{worker_id}] ⚠️ No guild_members table found in original database")
            
            original_conn.close()

        print(f"[{worker_id}] Processing {len(individual_categories)} individual metrics in parallel...")
        
        # Since we already have calculated ratings in our temp database, use it directly
        # instead of calling get_filtered_leaderboard_data which recalculates everything
        print(f"[{worker_id}] Processing {len(individual_categories)} individual metrics directly from temp database...")
        
        for category in individual_categories:
            print(f"[{worker_id}] Processing metric: {category}")
            # Use the temp database directly instead of recalculating
            results = get_glicko_leaderboard_data(db_path, category, limit=100, date_filter=None)  # No date filter since db is already filtered
            filter_data["individual_metrics"][category] = [
                {
                    "rank": i + 1,
                    "account_name": account,
                    "profession": profession,
                    "composite_score": float(composite),
                    "glicko_rating": float(rating),
                    "games_played": int(games),
                    "average_rank_percent": float(avg_rank) if avg_rank > 0 else None,
                    "average_stat_value": float(avg_stat) if avg_stat > 0 else None,
                    "is_guild_member": bool(is_guild_member)
                }
                for i, (account, profession, composite, rating, games, avg_rank, avg_stat, is_guild_member) in enumerate(results)
            ]

        results = get_glicko_leaderboard_data(db_path, "Overall", limit=100, date_filter=None)  # Use temp db directly
        filter_data["overall_leaderboard"] = [
            {
                "rank": i + 1,
                "account_name": account,
                "profession": profession,
                "composite_score": float(composite),
                "glicko_rating": float(rating),
                "games_played": int(games),
                "average_rank_percent": float(avg_rank) if avg_rank > 0 else None,
                "average_stat_value": float(avg_stat) if avg_stat > 0 else None,
                "is_guild_member": bool(is_guild_member)
            }
            for i, (account, profession, composite, rating, games, avg_rank, avg_stat, is_guild_member) in enumerate(results)
        ]

        print(f"[{worker_id}] Processing profession leaderboards in parallel...")
        # Process key professions (can be configured based on performance needs)
        professions_to_process = ["Firebrand", "Chronomancer", "Scourge", "Druid", "Condi Firebrand", "Support Spb"]  # Most common WvW professions
        
        # Process professions in parallel within each filter
        with ThreadPoolExecutor(max_workers=min(len(professions_to_process), 3)) as prof_executor:
            prof_futures = {
                prof_executor.submit(_process_single_profession, db_path, profession, filter_value, worker_id, worker_progress_callback): profession
                for profession in professions_to_process
            }
            
            completed_professions = 0
            for future in as_completed(prof_futures):
                profession = prof_futures[future]
                try:
                    prof_data = future.result()
                    completed_professions += 1
                    from datetime import datetime
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    if prof_data:
                        filter_data["profession_leaderboards"][profession] = prof_data
                        print(f"[{worker_id}] ✅ {timestamp} Profession {profession} completed ({completed_professions}/{len(prof_futures)})")
                    else:
                        print(f"[{worker_id}] ⚠️ {timestamp} Profession {profession} returned no data ({completed_professions}/{len(prof_futures)})")
                except Exception as e:
                    completed_professions += 1
                    from datetime import datetime
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{worker_id}] ❌ {timestamp} Profession {profession} failed ({completed_professions}/{len(prof_futures)}): {e}")
                    filter_data["profession_leaderboards"][profession] = None

        print(f"[{worker_id}] Processing high scores...")
        # Get high scores data (top burst damage records) with date filtering
        high_scores_results = get_high_scores_data(db_path, limit=100, date_filter=filter_value)
        filter_data["high_scores"]["Highest 1 Sec Burst"] = [
            {
                "rank": i + 1,
                "account_name": account,
                "profession": profession,
                "burst_damage": int(burst_damage),
                "timestamp": timestamp,
                "is_guild_member": bool(is_guild_member)
            }
            for i, (account, profession, burst_damage, timestamp, is_guild_member) in enumerate(high_scores_results)
        ]
        
        # Get new high scores data (skill damage and single fight DPS) with date filtering
        new_high_scores_results = get_new_high_scores_data(db_path, limit=100, date_filter=filter_value)
        for metric_name, metric_data in new_high_scores_results.items():
            filter_data["high_scores"][metric_name] = metric_data
        
        print(f"[{worker_id}] Worker completed successfully")
        return filter_data
    
    finally:
        # Cleanup temporary database
        if temp_db_path:
            try:
                import os
                os.unlink(temp_db_path)
                print(f"[{worker_id}] Cleaned up temporary database: {temp_db_path}")
            except Exception as e:
                print(f"[{worker_id}] Warning: Could not cleanup temporary database {temp_db_path}: {e}")


def generate_html_ui(data: Dict[str, Any], output_dir: Path):
    """Generate the HTML UI files."""
    output_dir.mkdir(exist_ok=True)
    
    # Generate main HTML file
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GW2 WvW Leaderboards</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <div class="header-text">
                    <h1>🏆 GW2 WvW Leaderboards</h1>
                    <p class="subtitle">Glicko-based rating system for World vs World performance</p>
                    <p class="last-updated">Last updated: <span id="lastUpdated"></span></p>
                </div>
                <button class="dark-mode-toggle" id="darkModeToggle" aria-label="Toggle dark mode">
                    <span class="toggle-icon">🌙</span>
                </button>
            </div>
        </header>

        <nav class="nav-tabs">
            <button class="tab-button active" data-tab="individual">Individual Metrics</button>
            <button class="tab-button" data-tab="high-scores">High Scores</button>
            <button class="tab-button" data-tab="professions">Professions</button>
            <button class="tab-button" data-tab="about">About</button>
        </nav>

        <div class="date-filters">
            <span class="filter-label">Time Period:</span>
            <button class="date-filter-button active" data-filter="overall">All Time</button>
            <button class="date-filter-button" data-filter="30d">Last 30 Days</button>
            <button class="date-filter-button" data-filter="90d">Last 90 Days</button>
            <button class="date-filter-button" data-filter="180d">Last 180 Days</button>
        </div>

        <div class="guild-filters" id="guild-filters" style="display: none;">
            <span class="filter-label">Players:</span>
            <button class="guild-filter-button active" data-guild-filter="all_players">All Players</button>
            <button class="guild-filter-button" data-guild-filter="guild_members" id="guild-members-button">Guild Members Only</button>
        </div>

        <main>
            <!-- Individual Metrics -->
            <div id="individual" class="tab-content active">
                <h2>Individual Metrics</h2>
                <p class="description">Rankings by specific performance metrics.</p>
                
                <div class="metric-selector">
                    <button class="metric-button active" data-metric="DPS">DPS</button>
                    <button class="metric-button" data-metric="Healing">Healing</button>
                    <button class="metric-button" data-metric="Barrier">Barrier</button>
                    <button class="metric-button" data-metric="Cleanses">Cleanses</button>
                    <button class="metric-button" data-metric="Strips">Strips</button>
                    <button class="metric-button" data-metric="Stability">Stability</button>
                    <button class="metric-button" data-metric="Resistance">Resistance</button>
                    <button class="metric-button" data-metric="Might">Might</button>
                    <button class="metric-button" data-metric="Protection">Protection</button>
                    <button class="metric-button" data-metric="Downs">DownCont</button>
                    <button class="metric-button" data-metric="Burst Consistency">Burst Consistency</button>
                </div>
                
                <div id="individual-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- High Scores -->
            <div id="high-scores" class="tab-content">
                <h2>High Scores</h2>
                <p class="description">Top performance records across different categories (non-Glicko based).</p>
                
                <div class="metric-selector">
                    <button class="metric-button active" data-metric="Highest 1 Sec Burst">Highest 1 Sec Burst</button>
                    <button class="metric-button" data-metric="Highest Outgoing Skill Damage">Highest Outgoing Skill Damage</button>
                    <button class="metric-button" data-metric="Highest Incoming Skill Damage">Highest Incoming Skill Damage</button>
                    <button class="metric-button" data-metric="Highest Single Fight DPS">Highest Single Fight DPS</button>
                </div>
                
                <div id="high-scores-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- Profession Leaderboards -->
            <div id="professions" class="tab-content">
                <h2>Profession Leaderboards</h2>
                <p class="description">Role-specific rankings with weighted metrics for each profession.</p>
                
                <div class="profession-selector">
                    <button class="profession-button active" data-profession="Firebrand">Firebrand</button>
                    <button class="profession-button" data-profession="Chronomancer">Chronomancer</button>
                    <button class="profession-button" data-profession="Scourge">Scourge</button>
                    <button class="profession-button" data-profession="Druid">Druid</button>
                    <button class="profession-button" data-profession="Condi Firebrand">Condi Firebrand</button>
                    <button class="profession-button" data-profession="Support Spb">Support Spb</button>
                </div>
                
                <div id="profession-info" class="profession-info"></div>
                <div id="profession-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- About -->
            <div id="about" class="tab-content">
                <h2>About the Rating System</h2>
                <div class="about-content">
                    <h3>🎯 Methodology</h3>
                    <p>This leaderboard uses a <strong>Glicko-2 rating system</strong> combined with session-based z-score evaluation to rank World vs World performance. Each player's skill is evaluated relative to their peers in the same combat sessions, ensuring fair comparisons across different battle contexts.</p>
                    
                    <h3>📊 How It Works</h3>
                    <ul>
                        <li><strong>Session-Based Evaluation:</strong> Each combat session is analyzed independently to calculate player rankings within that specific battle</li>
                        <li><strong>Z-Score Calculation:</strong> Player performance is normalized using z-scores: <code>(player_value - session_mean) / session_std</code></li>
                        <li><strong>Glicko-2 Rating:</strong> Dynamic rating system starting at 1500 that increases/decreases based on performance outcomes converted from z-scores</li>
                        <li><strong>Rating Deviation (RD):</strong> Measures uncertainty in a player's rating (starts at 350, decreases with more games)</li>
                    </ul>
                    
                    <h3>🏅 Leaderboard Types</h3>
                    <ul>
                        <li><strong>Individual Metrics:</strong> Rankings for specific performance areas (DPS, Healing, Barrier, Cleanses, Strips, Stability, Resistance, Might, Protection, Down Contribution, Burst Consistency)</li>
                        <li><strong>High Scores:</strong> Record-breaking single performance instances (highest burst damage, skill damage, single-fight DPS)</li>
                        <li><strong>Profession-Specific:</strong> Role-based rankings using weighted combinations of relevant metrics for each profession</li>
                        <li><strong>Time Filters:</strong> All-time, 30-day, 90-day, and 180-day rankings to show recent vs historical performance</li>
                        <li><strong>Player Summaries:</strong> Click any player name to view detailed performance breakdowns by profession and metric</li>
                    </ul>
                    
                    <h3>📈 Key Metrics Explained</h3>
                    <ul>
                        <li><strong>Glicko Rating:</strong> Base skill rating around 1500 ± 500 (higher = more skilled, used for primary ranking)</li>
                        <li><strong>Raids:</strong> Number of combat sessions analyzed (more sessions = lower uncertainty in rating)</li>
                        <li><strong>Avg Rank:</strong> Average percentile rank in sessions (lower percentage = consistently better performance)</li>
                        <li><strong>Avg Stat:</strong> Average raw statistical value for the specific metric being ranked</li>
                        <li><strong>Rating Deviation:</strong> Uncertainty measure that decreases with more games played</li>
                    </ul>
                    
                    <h3>⚖️ Fairness Features</h3>
                    <ul>
                        <li><strong>Context-Aware:</strong> Performance evaluated relative to session participants, not absolute values</li>
                        <li><strong>Battle-Type Neutral:</strong> Works equally well for GvG fights, zerg battles, and keep sieges</li>
                        <li><strong>Skill-Based Rankings:</strong> Pure Glicko-2 ratings without artificial bonuses or penalties</li>
                        <li><strong>Uncertainty Handling:</strong> Rating Deviation ensures new/infrequent players don't dominate experienced players</li>
                        <li><strong>Profession Recognition:</strong> Automatic detection of build variants (China DH, Boon Vindicator, etc.)</li>
                    </ul>
                </div>
            </div>
        </main>

        <!-- Player Detail Modal -->
        <div id="player-modal" class="modal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="player-modal-title">Player Details</h2>
                    <button class="modal-close" aria-label="Close modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="player-summary-content">
                        <div class="player-overview">
                            <div class="player-info-card">
                                <h3>Overview</h3>
                                <div id="player-overview-content"></div>
                            </div>
                            <div class="player-activity-card">
                                <h3>Activity</h3>
                                <div id="player-activity-content"></div>
                            </div>
                        </div>
                        
                        <div class="player-metrics">
                            <h3>Performance Metrics</h3>
                            <div class="profession-filter" id="profession-filter" style="margin-bottom: 15px;">
                            </div>
                            <div id="player-metrics-content"></div>
                        </div>
                        
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="script.js"></script>
</body>
</html>"""

    # Generate CSS file
    css_content = """:root {
    --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --main-bg: #ffffff;
    --text-color: #333333;
    --text-color-secondary: #666666;
    --text-color-light: #ffffff;
    --card-bg: #ffffff;
    --border-color: #dee2e6;
    --hover-bg: #f8f9fa;
    --button-bg: rgba(255,255,255,0.2);
    --button-border: rgba(255,255,255,0.3);
    --button-hover: rgba(255,255,255,0.3);
    --button-active: rgba(255,255,255,0.4);
    --shadow: 0 10px 30px rgba(0,0,0,0.2);
}

[data-theme="dark"] {
    --bg-gradient: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
    --main-bg: #2c3e50;
    --text-color: #ecf0f1;
    --text-color-secondary: #bdc3c7;
    --text-color-light: #ffffff;
    --card-bg: #34495e;
    --border-color: #4a6741;
    --hover-bg: #3c5a99;
    --button-bg: rgba(255,255,255,0.1);
    --button-border: rgba(255,255,255,0.2);
    --button-hover: rgba(255,255,255,0.2);
    --button-active: rgba(255,255,255,0.3);
    --shadow: 0 10px 30px rgba(0,0,0,0.4);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background: var(--bg-gradient);
    min-height: 100vh;
    transition: all 0.3s ease;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    margin-bottom: 30px;
    color: var(--text-color-light);
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
}

.header-text {
    text-align: center;
    flex: 1;
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 10px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

.subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    margin-bottom: 10px;
}

.last-updated {
    font-size: 0.9rem;
    opacity: 0.8;
}

.dark-mode-toggle {
    background: var(--button-bg);
    border: 2px solid var(--button-border);
    border-radius: 50px;
    padding: 12px 16px;
    cursor: pointer;
    transition: all 0.3s ease;
    color: var(--text-color-light);
    font-size: 1.2rem;
    min-width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.dark-mode-toggle:hover {
    background: var(--button-hover);
    border-color: rgba(255,255,255,0.5);
    transform: scale(1.05);
}

.toggle-icon {
    transition: transform 0.3s ease;
    font-size: 1.2rem;
}

.nav-tabs {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
    background: var(--button-bg);
    border-radius: 10px;
    padding: 10px;
    backdrop-filter: blur(10px);
}

.date-filters, .guild-filters {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 20px;
    background: var(--button-bg);
    border-radius: 10px;
    padding: 15px;
    backdrop-filter: blur(10px);
    flex-wrap: wrap;
    gap: 10px;
}

.guild-filters {
    margin-bottom: 30px;
}

.filter-label {
    color: var(--text-color-light);
    font-weight: bold;
    margin-right: 15px;
    font-size: 1rem;
}

.date-filter-button, .guild-filter-button {
    background: var(--button-bg);
    border: 2px solid var(--button-border);
    padding: 8px 16px;
    border-radius: 6px;
    color: var(--text-color-light);
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.date-filter-button:hover, .guild-filter-button:hover {
    background: var(--button-hover);
    border-color: rgba(255,255,255,0.5);
}

.date-filter-button.active, .guild-filter-button.active {
    background: var(--button-active);
    border-color: rgba(255,255,255,0.6);
    font-weight: bold;
}

.tab-button {
    background: transparent;
    border: none;
    padding: 12px 24px;
    margin: 0 5px;
    border-radius: 8px;
    color: var(--text-color-light);
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.tab-button:hover {
    background: var(--button-hover);
}

.tab-button.active {
    background: var(--button-active);
    font-weight: bold;
}

main {
    background: var(--main-bg);
    border-radius: 15px;
    padding: 30px;
    box-shadow: var(--shadow);
    min-height: 600px;
    transition: all 0.3s ease;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

h2 {
    color: var(--text-color);
    margin-bottom: 10px;
    font-size: 1.8rem;
}

.description {
    color: var(--text-color-secondary);
    margin-bottom: 25px;
    font-size: 1.1rem;
}

.metric-selector, .profession-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 25px;
    justify-content: center;
}

.metric-button, .profession-button {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.9rem;
    color: var(--text-color);
}

.metric-button:hover, .profession-button:hover {
    background: var(--hover-bg);
    border-color: var(--text-color-secondary);
}

.metric-button.active, .profession-button.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.profession-info {
    background: var(--card-bg);
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    border-left: 4px solid #667eea;
    border: 1px solid var(--border-color);
}

.profession-info h3 {
    margin-bottom: 10px;
    color: var(--text-color);
}

.profession-info p {
    color: var(--text-color-secondary);
    margin-bottom: 5px;
}

.leaderboard-container {
    overflow-x: auto;
}

.leaderboard-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.leaderboard-table th,
.leaderboard-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-color);
}

.leaderboard-table th {
    background: var(--card-bg);
    font-weight: bold;
    color: var(--text-color);
    position: sticky;
    top: 0;
    border-bottom: 2px solid var(--border-color);
}

.leaderboard-table tr:hover {
    background: var(--hover-bg);
}

.rank-cell {
    font-weight: bold;
    color: #667eea;
    width: 60px;
}

.account-cell {
    font-weight: 500;
    min-width: 200px;
}

.account-link {
    color: var(--text-color);
    text-decoration: none;
    transition: all 0.3s ease;
    border-radius: 4px;
    padding: 2px 4px;
}

.account-link:hover {
    color: #667eea;
    background: var(--hover-bg);
    text-decoration: none;
}

.profession-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
    text-transform: uppercase;
    margin-left: 10px;
    gap: 4px;
    white-space: nowrap;
}

.profession-icon {
    width: 16px;
    height: 16px;
    border-radius: 2px;
}

.stat-value {
    font-family: 'Courier New', monospace;
    font-weight: bold;
}

.rank-percent {
    color: #28a745;
    font-weight: bold;
}

.rank-percent.poor {
    color: #dc3545;
}

.rank-percent.average {
    color: #ffc107;
}

.raids-value {
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 3px;
}

.guild-yes {
    color: #28a745;
    font-weight: bold;
}

.guild-no {
    color: #6c757d;
    font-weight: normal;
}

.about-content {
    line-height: 1.8;
}

.about-content h3 {
    color: #667eea;
    margin: 25px 0 15px 0;
    font-size: 1.3rem;
}

.about-content ul {
    margin-left: 20px;
    margin-bottom: 20px;
}

.about-content li {
    margin-bottom: 8px;
}

.about-content strong {
    color: var(--text-color);
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .header-content {
        flex-direction: column;
        text-align: center;
    }
    
    .dark-mode-toggle {
        align-self: center;
        margin-top: 10px;
    }
    
    header h1 {
        font-size: 2rem;
    }
    
    .nav-tabs {
        flex-wrap: wrap;
        gap: 5px;
    }
    
    .tab-button {
        padding: 10px 16px;
        font-size: 0.9rem;
    }
    
    main {
        padding: 20px;
    }
    
    .metric-selector, .profession-selector {
        justify-content: flex-start;
    }
    
    .metric-button, .profession-button {
        padding: 8px 16px;
        font-size: 0.8rem;
    }
    
    .leaderboard-table th,
    .leaderboard-table td {
        padding: 8px;
        font-size: 0.9rem;
    }
    
    .account-cell {
        min-width: 150px;
    }
}

/* Player Detail Modal */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.7);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.3s ease;
}

.modal-content {
    background: var(--main-bg);
    border-radius: 15px;
    box-shadow: var(--shadow);
    max-width: 95vw;
    max-height: 90vh;
    width: 1200px;
    overflow: hidden;
    animation: slideIn 0.3s ease;
}

.modal-header {
    padding: 20px 30px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--hover-bg);
}

.modal-header h2 {
    margin: 0;
    color: var(--text-color);
    font-size: 1.5rem;
}

.modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: var(--text-color);
    cursor: pointer;
    padding: 5px;
    border-radius: 50%;
    width: 35px;
    height: 35px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s ease;
}

.modal-close:hover {
    background: var(--hover-bg);
}

.modal-body {
    padding: 30px;
    overflow-y: auto;
    max-height: calc(90vh - 100px);
}

.player-summary-content {
    display: flex;
    flex-direction: column;
    gap: 30px;
}

.player-overview {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.player-info-card, .player-activity-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 20px;
}

.player-info-card h3, .player-activity-card h3, 
.player-metrics h3, .player-professions h3, .player-sessions h3 {
    margin: 0 0 15px 0;
    color: #667eea;
    font-size: 1.2rem;
    border-bottom: 2px solid #667eea;
    padding-bottom: 5px;
}

.player-metrics, .player-professions, .player-sessions {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 20px;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
}

.metric-item {
    background: var(--hover-bg);
    padding: 15px;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}

.metric-name {
    font-weight: bold;
    color: var(--text-color);
    margin-bottom: 5px;
}

.metric-value {
    color: var(--text-color-secondary);
    font-size: 0.9rem;
}

.profession-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.profession-tab {
    background: var(--button-bg);
    border: 1px solid var(--button-border);
    padding: 8px 16px;
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: var(--text-color);
}

.profession-tab:hover {
    background: var(--button-hover);
}

.profession-tab.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.sessions-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.sessions-table th,
.sessions-table td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

.sessions-table th {
    background: var(--hover-bg);
    font-weight: bold;
    color: var(--text-color);
}

.clickable-name {
    color: #667eea;
    cursor: pointer;
    text-decoration: none;
    transition: color 0.2s ease;
}

.clickable-name:hover {
    color: #5a67d8;
    text-decoration: underline;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideIn {
    from { 
        opacity: 0;
        transform: translateY(-50px) scale(0.95);
    }
    to { 
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

/* Mobile responsive for modal */
@media (max-width: 768px) {
    .modal-content {
        max-width: 95vw;
        max-height: 95vh;
        margin: 10px;
    }
    
    .modal-header {
        padding: 15px 20px;
    }
    
    .modal-body {
        padding: 20px;
        max-height: calc(95vh - 80px);
    }
    
    .player-overview {
        grid-template-columns: 1fr;
        gap: 15px;
    }
    
    .metric-grid {
        grid-template-columns: 1fr;
    }
    
    .profession-tabs {
        gap: 5px;
    }
    
    .profession-tab {
        padding: 6px 12px;
        font-size: 0.9rem;
    }
}

/* Profession Filter Buttons */
.profession-filter {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
}

.profession-filter-btn {
    background: var(--button-bg);
    border: 1px solid var(--button-border);
    padding: 6px 12px;
    border-radius: 15px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: var(--text-color);
    font-size: 0.85rem;
}

.profession-filter-btn:hover {
    background: var(--button-hover);
}

.profession-filter-btn.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

@media (max-width: 768px) {
    .profession-filter {
        gap: 4px;
    }
    
    .profession-filter-btn {
        padding: 4px 8px;
        font-size: 0.8rem;
    }
}"""

    # Generate JavaScript file
    js_content = f"""// Leaderboard data
const leaderboardData = {json.dumps(data, indent=2)};

// Current state
let currentDateFilter = 'overall';
let currentTab = 'individual';
let currentMetric = 'DPS';
let currentProfession = 'Firebrand';
let currentHighScore = 'Highest 1 Sec Burst';
let currentGuildFilter = 'all_players';

// GW2 Wiki profession icons
const professionIcons = {{
    'Guardian': 'https://wiki.guildwars2.com/images/c/c7/Guardian_icon_small.png',
    'Dragonhunter': 'https://wiki.guildwars2.com/images/5/5d/Dragonhunter_icon_small.png',
    'China DH': 'https://wiki.guildwars2.com/images/5/5d/Dragonhunter_icon_small.png',
    'Firebrand': 'https://wiki.guildwars2.com/images/0/0e/Firebrand_icon_small.png',
    'Willbender': 'https://wiki.guildwars2.com/images/c/c7/Guardian_icon_small.png', // Fallback to Guardian
    'Warrior': 'https://wiki.guildwars2.com/images/4/45/Warrior_icon_small.png',
    'Berserker': 'https://wiki.guildwars2.com/images/a/a8/Berserker_icon_small.png',
    'Spellbreaker': 'https://wiki.guildwars2.com/images/0/08/Spellbreaker_icon_small.png',
    'Bladesworn': 'https://wiki.guildwars2.com/images/c/cf/Bladesworn_icon_small.png',
    'Engineer': 'https://wiki.guildwars2.com/images/0/07/Engineer_icon_small.png',
    'Scrapper': 'https://wiki.guildwars2.com/images/7/7d/Scrapper_icon_small.png',
    'Holosmith': 'https://wiki.guildwars2.com/images/a/aa/Holosmith_icon_small.png',
    'Mechanist': 'https://wiki.guildwars2.com/images/6/6d/Mechanist_icon_small.png',
    'Ranger': 'https://wiki.guildwars2.com/images/1/1e/Ranger_icon_small.png',
    'Druid': 'https://wiki.guildwars2.com/images/9/9b/Druid_icon_small.png',
    'Soulbeast': 'https://wiki.guildwars2.com/images/f/f6/Soulbeast_icon_small.png',
    'Untamed': 'https://wiki.guildwars2.com/images/2/2d/Untamed_icon_small.png',
    'Thief': 'https://wiki.guildwars2.com/images/7/7a/Thief_icon_small.png',
    'Daredevil': 'https://wiki.guildwars2.com/images/f/f3/Daredevil_icon_small.png',
    'Deadeye': 'https://wiki.guildwars2.com/images/7/70/Deadeye_icon_small.png',
    'Specter': 'https://wiki.guildwars2.com/images/6/61/Specter_icon_small.png',
    'Elementalist': 'https://wiki.guildwars2.com/images/4/4e/Elementalist_icon_small.png',
    'Tempest': 'https://wiki.guildwars2.com/images/5/58/Tempest_icon_small.png',
    'Weaver': 'https://wiki.guildwars2.com/images/c/c3/Weaver_icon_small.png',
    'Catalyst': 'https://wiki.guildwars2.com/images/c/c5/Catalyst_icon_small.png',
    'Mesmer': 'https://wiki.guildwars2.com/images/7/79/Mesmer_icon_small.png',
    'Chronomancer': 'https://wiki.guildwars2.com/images/e/e0/Chronomancer_icon_small.png',
    'Mirage': 'https://wiki.guildwars2.com/images/c/c8/Mirage_icon_small.png',
    'Virtuoso': 'https://wiki.guildwars2.com/images/a/a7/Virtuoso_icon_small.png',
    'Necromancer': 'https://wiki.guildwars2.com/images/1/10/Necromancer_icon_small.png',
    'Reaper': 'https://wiki.guildwars2.com/images/9/93/Reaper_icon_small.png',
    'Scourge': 'https://wiki.guildwars2.com/images/e/e8/Scourge_icon_small.png',
    'Harbinger': 'https://wiki.guildwars2.com/images/1/1d/Harbinger_icon_small.png',
    'Revenant': 'https://wiki.guildwars2.com/images/4/4c/Revenant_icon_small.png',
    'Herald': 'https://wiki.guildwars2.com/images/3/39/Herald_icon_small.png',
    'Renegade': 'https://wiki.guildwars2.com/images/b/be/Renegade_icon_small.png',
    'Vindicator': 'https://wiki.guildwars2.com/images/6/6d/Vindicator_icon_small.png',
    'Condi Firebrand': 'https://wiki.guildwars2.com/images/0/0e/Firebrand_icon_small.png',
    'Support Spb': 'https://wiki.guildwars2.com/images/0/08/Spellbreaker_icon_small.png'
}};

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {{
    initializePage();
    setupEventListeners();
    loadCurrentData();
}});

function initializePage() {{
    // Set last updated time
    const lastUpdated = new Date(leaderboardData.generated_at);
    document.getElementById('lastUpdated').textContent = lastUpdated.toLocaleString();
    
    // Initialize dark mode from localStorage
    initializeDarkMode();
    
    // Initialize guild filtering if enabled
    if (leaderboardData.guild_enabled) {{
        const guildFilters = document.getElementById('guild-filters');
        guildFilters.style.display = 'flex';
        
        // Update guild member button text
        const guildButton = document.getElementById('guild-members-button');
        guildButton.textContent = `${{leaderboardData.guild_tag}} Members Only`;
    }}
}}

function initializeDarkMode() {{
    // Check for saved theme preference or default to light mode
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateToggleIcon(savedTheme);
}}

function toggleDarkMode() {{
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateToggleIcon(newTheme);
    
    // Reapply raids gradient with new theme colors
    setTimeout(() => applyRaidsGradient(), 50);
}}

function updateToggleIcon(theme) {{
    const toggleIcon = document.querySelector('.toggle-icon');
    if (theme === 'dark') {{
        toggleIcon.textContent = '☀️';
    }} else {{
        toggleIcon.textContent = '🌙';
    }}
}}

function setupEventListeners() {{
    // Dark mode toggle
    document.getElementById('darkModeToggle').addEventListener('click', toggleDarkMode);
    
    // Tab navigation
    document.querySelectorAll('.tab-button').forEach(button => {{
        button.addEventListener('click', function() {{
            switchTab(this.dataset.tab);
        }});
    }});
    
    // Date filter selection
    document.querySelectorAll('.date-filter-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectDateFilter(this.dataset.filter);
        }});
    }});
    
    // Metric selection - handle individual metrics and high scores separately
    document.querySelectorAll('#individual .metric-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectMetric(this.dataset.metric);
        }});
    }});
    
    // High score selection
    document.querySelectorAll('#high-scores .metric-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectHighScore(this.dataset.metric);
        }});
    }});
    
    // Profession selection
    document.querySelectorAll('.profession-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectProfession(this.dataset.profession);
        }});
    }});
    
    // Guild filter selection
    document.querySelectorAll('.guild-filter-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectGuildFilter(this.dataset.guildFilter);
        }});
    }});
}}

function selectDateFilter(filter) {{
    currentDateFilter = filter;
    document.querySelectorAll('.date-filter-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-filter="${{filter}}"]`).classList.add('active');
    loadCurrentData();
}}

function selectGuildFilter(guildFilter) {{
    currentGuildFilter = guildFilter;
    document.querySelectorAll('.guild-filter-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-guild-filter="${{guildFilter}}"]`).classList.add('active');
    loadCurrentData();
}}

function getCurrentData() {{
    return leaderboardData.date_filters[currentDateFilter];
}}

function getCurrentDateFilter() {{
    return currentDateFilter;
}}

function filterDataByGuildMembership(data) {{
    if (!leaderboardData.guild_enabled || currentGuildFilter === 'all_players') {{
        return data;
    }}
    
    // Filter to guild members only
    return data.filter(player => player.is_guild_member === true);
}}

function switchTab(tabName) {{
    currentTab = tabName;
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-tab="${{tabName}}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    
    loadCurrentData();
}}

function selectMetric(metric) {{
    currentMetric = metric;
    currentHighScore = metric;  // Also update high score selection
    document.querySelectorAll('.metric-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-metric="${{metric}}"]`).classList.add('active');
    if (currentTab === 'individual') {{
        loadIndividualMetric(metric);
    }} else if (currentTab === 'high-scores') {{
        loadHighScores(metric);
    }}
}}

function selectHighScore(metric) {{
    currentHighScore = metric;
    // For high scores tab, update the metric buttons in the high scores section
    if (currentTab === 'high-scores') {{
        document.querySelectorAll('#high-scores .metric-button').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`#high-scores [data-metric="${{metric}}"]`).classList.add('active');
        loadHighScores(metric);
    }}
}}

function selectProfession(profession) {{
    currentProfession = profession;
    document.querySelectorAll('.profession-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-profession="${{profession}}"]`).classList.add('active');
    if (currentTab === 'professions') {{
        loadProfessionLeaderboard(profession);
    }}
}}

function loadCurrentData() {{
    switch(currentTab) {{
        case 'overall':
            loadOverallLeaderboard();
            break;
        case 'individual':
            loadIndividualMetric(currentMetric);
            break;
        case 'high-scores':
            loadHighScores(currentHighScore);
            break;
        case 'professions':
            loadProfessionLeaderboard(currentProfession);
            break;
    }}
}}

function loadOverallLeaderboard() {{
    const container = document.getElementById('overall-leaderboard');
    const rawData = getCurrentData().overall_leaderboard;
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(rawData);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    const columns = [
        {{ key: 'rank', label: 'Rank', type: 'rank' }},
        {{ key: 'account_name', label: 'Account', type: 'account' }},
        {{ key: 'profession', label: 'Profession', type: 'profession' }},
        {{ key: 'glicko_rating', label: 'Glicko', type: 'number' }},
        {{ key: 'games_played', label: 'Raids', type: 'raids' }},
        {{ key: 'average_rank_percent', label: 'Avg Rank Per Raid', type: 'avg_rank' }}
    ];
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(3, 0, {{ key: 'is_guild_member', label: 'Guild Member', type: 'guild_member' }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns);
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function loadIndividualMetric(metric) {{
    const container = document.getElementById('individual-leaderboard');
    const rawData = getCurrentData().individual_metrics[metric];
    
    if (!rawData) {{
        container.innerHTML = '<p>No data available for this metric.</p>';
        return;
    }}
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(rawData);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    const columns = [
        {{ key: 'rank', label: 'Rank', type: 'rank' }},
        {{ key: 'account_name', label: 'Account', type: 'account' }},
        {{ key: 'profession', label: 'Profession', type: 'profession' }},
        {{ key: 'glicko_rating', label: 'Glicko', type: 'number' }},
        {{ key: 'games_played', label: 'Raids', type: 'raids' }},
        {{ key: 'average_rank_percent', label: 'Avg Rank', type: 'avg_rank' }},
        {{ key: 'average_stat_value', label: `Avg ${{metric === 'Downs' ? 'DownCont' : metric}}`, type: 'stat' }}
    ];
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(3, 0, {{ key: 'is_guild_member', label: 'Guild Member', type: 'guild_member' }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns);
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function loadProfessionLeaderboard(profession) {{
    const infoContainer = document.getElementById('profession-info');
    const container = document.getElementById('profession-leaderboard');
    const data = getCurrentData().profession_leaderboards[profession];
    
    if (!data) {{
        infoContainer.innerHTML = '<p>No data available for this profession.</p>';
        container.innerHTML = '';
        return;
    }}
    
    // Show profession info
    const metricsText = data.metrics.join(', ');
    const weightsText = data.weights.map(w => `${{(w * 100).toFixed(0)}}%`).join('/');
    
    infoContainer.innerHTML = `
        <h3>${{profession}} Metrics</h3>
        <p><strong>Weighted Metrics:</strong> ${{metricsText}}</p>
        <p><strong>Weights:</strong> ${{weightsText}}</p>
    `;
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(data.players);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    const columns = [
        {{ key: 'rank', label: 'Rank', type: 'rank' }},
        {{ key: 'account_name', label: 'Account', type: 'account' }},
        {{ key: 'glicko_rating', label: 'Glicko', type: 'number' }},
        {{ key: 'games_played', label: 'Raids', type: 'raids' }},
        {{ key: 'key_stats', label: 'Key Stats', type: 'stats' }}
    ];
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(2, 0, {{ key: 'is_guild_member', label: 'Guild Member', type: 'guild_member' }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns);
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function loadHighScores(metric) {{
    const container = document.getElementById('high-scores-leaderboard');
    const rawData = getCurrentData().high_scores[metric];
    
    if (!rawData || rawData.length === 0) {{
        container.innerHTML = '<p>No high scores data available.</p>';
        return;
    }}
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(rawData);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    // Define columns based on metric type
    let columns;
    if (metric === 'Highest 1 Sec Burst') {{
        columns = [
            {{ key: 'rank', label: 'Rank', type: 'rank' }},
            {{ key: 'account_name', label: 'Account', type: 'account' }},
            {{ key: 'profession', label: 'Profession', type: 'profession' }},
            {{ key: 'burst_damage', label: 'Burst Damage', type: 'number' }},
            {{ key: 'timestamp', label: 'Timestamp', type: 'stats' }}
        ];
    }} else if (metric === 'Highest Outgoing Skill Damage' || metric === 'Highest Incoming Skill Damage') {{
        columns = [
            {{ key: 'rank', label: 'Rank', type: 'rank' }},
            {{ key: 'player_name', label: 'Player', type: 'account' }},
            {{ key: 'profession', label: 'Profession', type: 'profession' }},
            {{ key: 'skill_name', label: 'Skill', type: 'stats' }},
            {{ key: 'score_value', label: 'Damage', type: 'number' }},
            {{ key: 'timestamp', label: 'Timestamp', type: 'stats' }}
        ];
    }} else if (metric === 'Highest Single Fight DPS') {{
        columns = [
            {{ key: 'rank', label: 'Rank', type: 'rank' }},
            {{ key: 'player_name', label: 'Player', type: 'account' }},
            {{ key: 'profession', label: 'Profession', type: 'profession' }},
            {{ key: 'score_value', label: 'DPS', type: 'number' }},
            {{ key: 'fight_number', label: 'Fight', type: 'stats' }},
            {{ key: 'timestamp', label: 'Timestamp', type: 'stats' }}
        ];
    }} else {{
        // Default columns for any other metrics
        columns = [
            {{ key: 'rank', label: 'Rank', type: 'rank' }},
            {{ key: 'account_name', label: 'Account', type: 'account' }},
            {{ key: 'profession', label: 'Profession', type: 'profession' }},
            {{ key: 'score_value', label: 'Score', type: 'number' }},
            {{ key: 'timestamp', label: 'Timestamp', type: 'stats' }}
        ];
    }}
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(3, 0, {{ key: 'is_guild_member', label: 'Guild Member', type: 'guild_member' }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns);
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function createLeaderboardTable(data, columns) {{
    if (!data || data.length === 0) {{
        return '<p>No data available.</p>';
    }}
    
    let html = '<table class="leaderboard-table"><thead><tr>';
    
    columns.forEach(col => {{
        html += `<th>${{col.label}}</th>`;
    }});
    
    html += '</tr></thead><tbody>';
    
    data.forEach(row => {{
        html += '<tr>';
        columns.forEach(col => {{
            const value = row[col.key];
            html += `<td class="${{col.type}}-cell">${{formatCellValue(value, col.type)}}</td>`;
        }});
        html += '</tr>';
    }});
    
    html += '</tbody></table>';
    
    // Apply raids gradient coloring after table creation
    setTimeout(() => applyRaidsGradient(), 10);
    
    return html;
}}

function formatCellValue(value, type) {{
    if (value === null || value === undefined) {{
        return 'N/A';
    }}
    
    switch (type) {{
        case 'rank':
            return `<span class="rank-cell">#${{value}}</span>`;
        case 'account':
            return `<span class="account-cell">${{value}}</span>`;
        case 'profession':
            const iconUrl = professionIcons[value] || '';
            const iconHtml = iconUrl ? `<img src="${{iconUrl}}" class="profession-icon" alt="${{value}}" onerror="this.style.display='none'">` : '';
            return `${{iconHtml}} ${{value}}`;
        case 'number':
            return Math.round(value);
        case 'raids':
            return `<span class="raids-value" data-raids="${{value}}">${{Math.round(value)}}</span>`;
        case 'percent':
            const percentClass = value < 25 ? 'rank-percent' : value > 75 ? 'rank-percent poor' : 'rank-percent average';
            return `<span class="${{percentClass}}">${{value.toFixed(1)}}%</span>`;
        case 'avg_rank':
            // Display actual average rank with 1 decimal place
            // Good ranks are low numbers (1-5), poor ranks are high numbers (10+)
            const rankClass = value <= 5 ? 'rank-percent' : value >= 10 ? 'rank-percent poor' : 'rank-percent average';
            return `<span class="${{rankClass}}">${{value.toFixed(1)}}</span>`;
        case 'stat':
            return `<span class="stat-value">${{value.toFixed(1)}}</span>`;
        case 'stats':
            return `<span class="stat-value">${{value}}</span>`;
        case 'guild_member':
            return value ? '<span class="guild-yes">✓ Yes</span>' : '<span class="guild-no">✗ No</span>';
        default:
            return value;
    }}
}}

function getProfessionColor(profession) {{
    const colors = {{
        'Firebrand': '#e74c3c',
        'Chronomancer': '#9b59b6',
        'Scourge': '#2c3e50',
        'Druid': '#27ae60',
        'Condi Firebrand': '#d35400',
        'Support Spb': '#f39c12',
        'Catalyst': '#3498db',
        'Weaver': '#e67e22',
        'Tempest': '#1abc9c',
        'Holosmith': '#34495e',
        'Dragonhunter': '#f1c40f',
        'Reaper': '#8e44ad',
        'Soulbeast': '#16a085',
        'Untamed': '#c0392b',
        'Spellbreaker': '#7f8c8d',
        'Berserker': '#e74c3c'
    }};
    return colors[profession] || '#95a5a6';
}}

function applyRaidsGradient() {{
    const raidsElements = document.querySelectorAll('.raids-value');
    if (raidsElements.length === 0) return;
    
    // Get all raids values and find min/max
    const raidsValues = Array.from(raidsElements).map(el => parseInt(el.dataset.raids));
    const minRaids = Math.min(...raidsValues);
    const maxRaids = Math.max(...raidsValues);
    
    // Check if we're in dark mode
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    
    // Apply gradient coloring
    raidsElements.forEach(element => {{
        const raids = parseInt(element.dataset.raids);
        const ratio = maxRaids === minRaids ? 0.5 : (raids - minRaids) / (maxRaids - minRaids);
        
        if (isDarkMode) {{
            // Dark mode: use brighter, more visible colors
            const red = Math.round(255 * (1 - ratio));
            const green = Math.round(255 * ratio);
            const blue = 50; // Add slight blue tint for better visibility
            
            element.style.backgroundColor = `rgba(${{red}}, ${{green}}, ${{blue}}, 0.4)`;
            element.style.color = ratio > 0.5 ? '#90ee90' : '#ffb3b3'; // Light green/red text
        }} else {{
            // Light mode: original colors
            const red = Math.round(255 * (1 - ratio));
            const green = Math.round(255 * ratio);
            const blue = 0;
            
            element.style.backgroundColor = `rgba(${{red}}, ${{green}}, ${{blue}}, 0.3)`;
            element.style.color = ratio > 0.5 ? '#2d5a2d' : '#5a2d2d'; // Dark green/red text
        }}
    }});
}}

// Player Modal Functions
function showPlayerModal(accountName) {{
    const modal = document.getElementById('player-modal');
    const title = document.getElementById('player-modal-title');
    
    // Set player name in title
    title.textContent = accountName + ' - Player Details';
    
    // Load player data from existing leaderboard data
    loadPlayerData(accountName);
    
    // Show modal
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
}}

function hidePlayerModal() {{
    const modal = document.getElementById('player-modal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto'; // Restore scrolling
}}

function loadPlayerData(accountName) {{
    const overviewContent = document.getElementById('player-overview-content');
    const activityContent = document.getElementById('player-activity-content');
    const metricsContent = document.getElementById('player-metrics-content');
    const professionFilter = document.getElementById('profession-filter');
    
    // Get current date filter
    const currentFilter = getCurrentDateFilter();
    const currentData = leaderboardData.date_filters[currentFilter];
    
    // Find player across ALL metrics and professions more thoroughly
    const allPlayerData = [];
    const playerProfessions = new Set();
    
    // Search individual metrics - collect ALL instances of this player
    Object.entries(currentData.individual_metrics).forEach(([metric, players]) => {{
        players.forEach(playerData => {{
            if (playerData.account_name === accountName) {{
                allPlayerData.push({{
                    ...playerData,
                    metric: metric,
                    source: 'individual'
                }});
                playerProfessions.add(playerData.profession);
            }}
        }});
    }});
    
    // Search profession leaderboards for additional profession coverage
    Object.entries(currentData.profession_leaderboards).forEach(([profession, data]) => {{
        const playerData = data.players.find(p => p.account_name === accountName);
        if (playerData) {{
            playerProfessions.add(profession);
        }}
    }});
    
    // Store all player data globally for filtering
    window.currentPlayerData = allPlayerData;
    window.currentPlayerProfessions = Array.from(playerProfessions);
    
    // Populate Overview
    const guildStatus = allPlayerData[0]?.is_guild_member ? 
        `<span style="color: #667eea;">✓ Guild Member</span>` : 
        `<span style="color: #999;">Non-Guild Member</span>`;
    
    overviewContent.innerHTML = `
        <div style="display: grid; gap: 10px;">
            <div><strong>Account:</strong> ${{accountName}}</div>
            <div><strong>Guild Status:</strong> ${{guildStatus}}</div>
            <div><strong>Professions Played:</strong> ${{Array.from(playerProfessions).join(', ')}}</div>
        </div>
    `;
    
    // Populate Activity
    const totalGames = allPlayerData.reduce((sum, data) => sum + (data.games_played || 0), 0);
    
    activityContent.innerHTML = `
        <div style="display: grid; gap: 10px;">
            <div><strong>Total Sessions:</strong> ${{totalGames}}</div>
            <div><strong>Metrics Found:</strong> ${{allPlayerData.length}}</div>
            <div><strong>Professions:</strong> ${{playerProfessions.size}}</div>
        </div>
    `;
    
    // Setup profession filter buttons
    professionFilter.innerHTML = '';
    
    const professionsArray = Array.from(playerProfessions);
    professionsArray.forEach((profession, index) => {{
        const count = allPlayerData.filter(d => d.profession === profession).length;
        const btn = document.createElement('button');
        btn.className = `profession-filter-btn ${{index === 0 ? 'active' : ''}}`;
        btn.setAttribute('data-profession', profession);
        btn.textContent = `${{profession}} (${{count}})`;
        btn.onclick = () => filterMetricsByProfession(profession);
        professionFilter.appendChild(btn);
    }});
    
    // Show first profession by default
    if (professionsArray.length > 0) {{
        filterMetricsByProfession(professionsArray[0]);
    }}
}}

function filterMetricsByProfession(profession) {{
    // Update active button
    document.querySelectorAll('.profession-filter-btn').forEach(btn => {{
        btn.classList.remove('active');
    }});
    document.querySelector(`[data-profession="${{profession}}"]`).classList.add('active');
    
    // Filter and display metrics
    const metricsContent = document.getElementById('player-metrics-content');
    const filteredData = window.currentPlayerData.filter(d => d.profession === profession);
    
    if (filteredData.length === 0) {{
        metricsContent.innerHTML = '<p style="color: var(--text-color-secondary); font-style: italic;">No metrics found for this profession.</p>';
        return;
    }}
    
    // Group by metric for cleaner display
    const metricGroups = {{}};
    filteredData.forEach(data => {{
        if (!metricGroups[data.metric]) {{
            metricGroups[data.metric] = [];
        }}
        metricGroups[data.metric].push(data);
    }});
    
    let metricsHtml = '<div class="metric-grid">';
    Object.entries(metricGroups).forEach(([metric, instances]) => {{
        // If multiple instances of same metric (different professions), show the best one
        const bestInstance = instances.reduce((best, current) => 
            current.rank < best.rank ? current : best
        );
        
        metricsHtml += `
            <div class="metric-item" data-profession="${{bestInstance.profession}}">
                <div class="metric-name">${{metric === 'Downs' ? 'DownCont' : metric}}</div>
                <div class="metric-value">
                    <div>Rank: #${{bestInstance.rank}}</div>
                    <div>Rating: ${{bestInstance.glicko_rating?.toFixed(0) || 'N/A'}}</div>
                    <div>Games: ${{bestInstance.games_played}}</div>
                    <div>Profession: ${{bestInstance.profession}}</div>
                    <div>Avg Value: ${{bestInstance.average_stat_value?.toFixed(1) || 'N/A'}}</div>
                </div>
            </div>
        `;
    }});
    metricsHtml += '</div>';
    metricsContent.innerHTML = metricsHtml;
}}

function makePlayerNamesClickable() {{
    // Make account names clickable in all leaderboard tables
    document.querySelectorAll('.account-cell').forEach(cell => {{
        if (cell.textContent && cell.textContent.trim() && !cell.querySelector('.clickable-name')) {{
            const accountName = cell.textContent.trim();
            cell.innerHTML = `<span class="clickable-name" onclick="showPlayerModal('${{accountName}}')">${{accountName}}</span>`;
        }}
    }});
}}

// Modal event listeners
document.addEventListener('DOMContentLoaded', function() {{
    // Close modal when clicking X
    document.querySelector('.modal-close').addEventListener('click', hidePlayerModal);
    
    // Close modal when clicking outside
    document.getElementById('player-modal').addEventListener('click', function(e) {{
        if (e.target === this) {{
            hidePlayerModal();
        }}
    }});
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape' && document.getElementById('player-modal').style.display === 'flex') {{
            hidePlayerModal();
        }}
    }});
    
    // Make initial player names clickable
    setTimeout(makePlayerNamesClickable, 100);
}});"""

    # Write all files
    (output_dir / "index.html").write_text(html_content)
    (output_dir / "styles.css").write_text(css_content)
    (output_dir / "script.js").write_text(js_content)
    
    print(f"HTML UI generated in: {output_dir}")
    print("Files created:")
    print("  - index.html")
    print("  - styles.css") 
    print("  - script.js")


def generate_player_detail_pages(output_dir: Path, player_summaries: List[str]):
    """Generate individual HTML pages for each player with embedded date filter data."""
    players_dir = output_dir / "players"
    
    if not players_dir.exists():
        print("No player summaries found, skipping player detail pages")
        return
    
    print(f"Generating player detail pages for {len(player_summaries)} players with embedded date filter data...")
    
    # Player detail page template
    player_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{PLAYER_NAME}} - GW2 WvW Leaderboards</title>
    <link rel="stylesheet" href="../styles.css">
    <style>
        /* Additional CSS custom properties for player pages */
        :root {
            --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --main-bg: #ffffff;
            --text-color: #333333;
            --text-color-secondary: #666666;
            --text-color-light: #ffffff;
            --card-bg: #ffffff;
            --border-color: #dee2e6;
            --hover-bg: #f8f9fa;
            --button-bg: rgba(255,255,255,0.2);
            --button-border: rgba(255,255,255,0.3);
            --button-hover: rgba(255,255,255,0.3);
            --button-active: rgba(255,255,255,0.4);
            --shadow: 0 10px 30px rgba(0,0,0,0.2);
        }

        [data-theme="dark"] {
            --bg-gradient: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            --main-bg: #2c3e50;
            --text-color: #ecf0f1;
            --text-color-secondary: #bdc3c7;
            --text-color-light: #ffffff;
            --card-bg: #34495e;
            --border-color: #4a6741;
            --hover-bg: #3c5a99;
            --button-bg: rgba(255,255,255,0.1);
            --button-border: rgba(255,255,255,0.2);
            --button-hover: rgba(255,255,255,0.2);
            --button-active: rgba(255,255,255,0.3);
            --shadow: 0 10px 30px rgba(0,0,0,0.4);
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background: var(--bg-gradient);
            min-height: 100vh;
            transition: all 0.3s ease;
        }

        .player-header {
            background: var(--bg-gradient);
            color: var(--text-color-light);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: var(--shadow);
        }
        
        .player-header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .player-subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-bottom: 20px;
        }
        
        .player-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stats-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s ease;
        }
        
        .stats-card:hover {
            box-shadow: var(--shadow);
            transform: translateY(-2px);
        }
        
        .stats-card h3 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.3rem;
        }
        
        .stat-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-color);
        }
        
        .stat-row:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        
        .stat-label {
            color: var(--text-color-secondary);
            font-weight: 500;
        }
        
        .stat-value {
            color: var(--text-color);
            font-weight: bold;
        }
        
        .metric-performance {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .metric-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        
        .metric-table th,
        .metric-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-color);
        }
        
        .metric-table th {
            background: var(--hover-bg);
            font-weight: bold;
        }
        
        .rank-good {
            color: #28a745;
            font-weight: bold;
        }
        
        .rank-average {
            color: #ffc107;
            font-weight: bold;
        }
        
        .rank-poor {
            color: #dc3545;
            font-weight: bold;
        }
        
        .profession-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        
        .profession-tag {
            background: #667eea;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        
        .profession-tabs {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
            justify-content: center;
        }
        
        .profession-tab-button {
            background: var(--card-bg);
            border: 2px solid var(--border-color);
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
            color: var(--text-color);
        }
        
        .profession-tab-button:hover {
            background: var(--hover-bg);
            border-color: var(--text-color-secondary);
        }
        
        .profession-tab-button.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        .profession-metric-table {
            display: none;
            margin-bottom: 20px;
        }
        
        .profession-metric-table.active {
            display: block;
        }
        
        .nav-buttons {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        
        .nav-button {
            background: var(--button-bg);
            border: 2px solid var(--button-border);
            color: var(--text-color-light);
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .nav-button:hover {
            background: var(--button-hover);
            border-color: rgba(255,255,255,0.5);
            text-decoration: none;
            color: var(--text-color-light);
        }
        
        .dark-mode-toggle {
            background: var(--button-bg);
            border: 2px solid var(--button-border);
            border-radius: 50px;
            padding: 12px 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            color: var(--text-color-light);
            font-size: 1.2rem;
            min-width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .dark-mode-toggle:hover {
            background: var(--button-hover);
            border-color: rgba(255,255,255,0.5);
            transform: scale(1.05);
        }

        .toggle-icon {
            transition: transform 0.3s ease;
            font-size: 1.2rem;
        }
        
        .date-filter-button:hover {
            background: var(--button-hover);
            border-color: rgba(255,255,255,0.5);
        }

        .date-filter-button.active {
            background: var(--button-active);
            border-color: rgba(255,255,255,0.6);
            font-weight: bold;
        }
        
        @media (max-width: 768px) {
            .player-stats-grid {
                grid-template-columns: 1fr;
            }
            
            .nav-buttons {
                flex-direction: column;
            }
            
            .player-header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav-buttons">
            <a href="../index.html" class="nav-button">← Back to Leaderboards</a>
            <button class="dark-mode-toggle" id="darkModeToggle" aria-label="Toggle dark mode">
                <span class="toggle-icon">🌙</span>
            </button>
        </div>
        
        <div class="date-filters" style="background: var(--button-bg); border-radius: 10px; padding: 15px; margin-bottom: 20px; backdrop-filter: blur(10px); display: flex; justify-content: center; flex-wrap: wrap; gap: 10px;">
            <span class="filter-label" style="color: var(--text-color-light); font-weight: bold; margin-right: 15px; font-size: 1rem;">Time Period:</span>
            <button class="date-filter-button active" data-filter="overall" style="background: var(--button-bg); border: 2px solid var(--button-border); padding: 8px 16px; border-radius: 6px; color: var(--text-color-light); font-size: 0.9rem; cursor: pointer; transition: all 0.3s ease;">All Time</button>
            <button class="date-filter-button" data-filter="30d" style="background: var(--button-bg); border: 2px solid var(--button-border); padding: 8px 16px; border-radius: 6px; color: var(--text-color-light); font-size: 0.9rem; cursor: pointer; transition: all 0.3s ease;">Last 30 Days</button>
            <button class="date-filter-button" data-filter="90d" style="background: var(--button-bg); border: 2px solid var(--button-border); padding: 8px 16px; border-radius: 6px; color: var(--text-color-light); font-size: 0.9rem; cursor: pointer; transition: all 0.3s ease;">Last 90 Days</button>
            <button class="date-filter-button" data-filter="180d" style="background: var(--button-bg); border: 2px solid var(--button-border); padding: 8px 16px; border-radius: 6px; color: var(--text-color-light); font-size: 0.9rem; cursor: pointer; transition: all 0.3s ease;">Last 180 Days</button>
        </div>
        
        <div class="player-header">
            <h1>{{PLAYER_NAME}}</h1>
            <p class="player-subtitle">Player Performance Summary</p>
            <div id="playerGuildInfo"></div>
        </div>
        
        <div class="player-stats-grid">
            <div class="stats-card">
                <h3>📊 Overview</h3>
                <div id="overviewStats"></div>
            </div>
            
            <div class="stats-card">
                <h3>🏆 Performance</h3>
                <div id="performanceStats"></div>
            </div>
            
            <div class="stats-card">
                <h3>📈 Activity</h3>
                <div id="activityStats"></div>
            </div>
        </div>
        
        <div class="metric-performance">
            <h3>🎯 Profession Performance</h3>
            <div class="profession-tabs" id="professionTabs"></div>
            <div id="professionMetricTables"></div>
        </div>
        
        <div class="stats-card">
            <h3>⚔️ Professions</h3>
            <div id="professionStats"></div>
        </div>
    </div>
    
    <script>
        const playerName = '{{PLAYER_NAME}}';
        const allPlayerData = {{ALL_PLAYER_DATA}};
        let currentDateFilter = 'overall';
        let playerData = allPlayerData.overall;
        
        // Initialize dark mode from localStorage - use same storage as main site
        function initializeDarkMode() {
            const savedTheme = localStorage.getItem('theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
            updateToggleIcon(savedTheme);
        }
        
        function toggleDarkMode() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateToggleIcon(newTheme);
        }
        
        function updateToggleIcon(theme) {
            const toggleIcon = document.querySelector('.toggle-icon');
            if (theme === 'dark') {
                toggleIcon.textContent = '☀️';
            } else {
                toggleIcon.textContent = '🌙';
            }
        }
        
        function formatNumber(value) {
            if (value >= 1000) {
                return (value / 1000).toFixed(1) + 'k';
            }
            return value.toFixed(1);
        }
        
        function getRankClass(percentile) {
            if (percentile >= 75) return 'rank-good';
            if (percentile >= 25) return 'rank-average';
            return 'rank-poor';
        }
        
        function loadProfessionMetrics() {
            const professionTabs = document.getElementById('professionTabs');
            const professionMetricTables = document.getElementById('professionMetricTables');
            
            // Clear existing content
            professionTabs.innerHTML = '';
            professionMetricTables.innerHTML = '';
            
            // Create tabs and tables for each profession
            playerData.profession_summaries.forEach((profSummary, index) => {
                // Create tab button
                const tabButton = document.createElement('button');
                tabButton.className = `profession-tab-button ${index === 0 ? 'active' : ''}`;
                tabButton.textContent = `${profSummary.profession} (${profSummary.sessions_played} sessions)`;
                tabButton.onclick = () => switchProfessionTab(profSummary.profession);
                professionTabs.appendChild(tabButton);
                
                // Create table container
                const tableContainer = document.createElement('div');
                tableContainer.className = `profession-metric-table ${index === 0 ? 'active' : ''}`;
                tableContainer.id = `table-${profSummary.profession.replace(/\\s+/g, '-')}`;
                
                tableContainer.innerHTML = `
                    <h4>📊 ${profSummary.profession} Performance</h4>
                    <div class="leaderboard-container">
                        <table class="metric-table">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Glicko Rating</th>
                                    <th>Games</th>
                                    <th>Average</th>
                                    <th>Best</th>
                                    <th>Rank</th>
                                    <th>Percentile</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${profSummary.metric_summaries.map(metric => {
                                    const rankClass = getRankClass(metric.percentile_rank);
                                    const sampleSizeWarning = metric.total_players <= 5 ? ' ⚠️' : '';
                                    const rankDisplay = metric.total_players <= 5 ? `#${metric.overall_rank}/${metric.total_players}` : `#${metric.overall_rank}`;
                                    const percentileDisplay = metric.total_players <= 5 ? `${metric.percentile_rank.toFixed(1)}% (${metric.total_players} players)` : `${metric.percentile_rank.toFixed(1)}%`;
                                    return `
                                        <tr>
                                            <td><strong>${metric.metric_name}${sampleSizeWarning}</strong></td>
                                            <td>${metric.glicko_rating.toFixed(0)}</td>
                                            <td>${metric.games_played}</td>
                                            <td>${formatNumber(metric.average_value)}</td>
                                            <td>${formatNumber(metric.best_value)}</td>
                                            <td class="${rankClass}">${rankDisplay}</td>
                                            <td class="${rankClass}">${percentileDisplay}</td>
                                        </tr>
                                    `;
                                }).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
                
                professionMetricTables.appendChild(tableContainer);
            });
        }
        
        function switchProfessionTab(profession) {
            // Update tab buttons
            document.querySelectorAll('.profession-tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Update table visibility
            document.querySelectorAll('.profession-metric-table').forEach(table => {
                table.classList.remove('active');
            });
            document.getElementById(`table-${profession.replace(/\\s+/g, '-')}`).classList.add('active');
        }
        
        function loadPlayerData() {
            // Guild info
            const guildInfo = document.getElementById('playerGuildInfo');
            if (playerData.profile.is_guild_member) {
                guildInfo.innerHTML = `<span style="color: #28a745; font-weight: bold;">Guild Member</span>`;
                if (playerData.profile.guild_rank) {
                    guildInfo.innerHTML += ` (${playerData.profile.guild_rank})`;
                }
            } else {
                guildInfo.innerHTML = `<span style="color: #6c757d;">Non-Guild Member</span>`;
            }
            
            // Overview stats
            const overviewStats = document.getElementById('overviewStats');
            overviewStats.innerHTML = `
                <div class="stat-row">
                    <span class="stat-label">Total Sessions:</span>
                    <span class="stat-value">${playerData.profile.total_sessions}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Activity Score:</span>
                    <span class="stat-value">${playerData.overall_stats.activity_score.toFixed(1)}/100</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Consistency:</span>
                    <span class="stat-value">${playerData.overall_stats.consistency_score.toFixed(1)}/100</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Activity Period:</span>
                    <span class="stat-value">${playerData.profile.activity_days} days</span>
                </div>
            `;
            
            // Performance stats
            const performanceStats = document.getElementById('performanceStats');
            
            // Find best metric by highest percentile
            let bestMetric = "N/A";
            let bestPercentile = 0;
            playerData.metric_summaries.forEach(metric => {
                if (metric.percentile_rank > bestPercentile) {
                    bestPercentile = metric.percentile_rank;
                    bestMetric = metric.metric_name;
                }
            });
            
            // Find average Glicko rating across all metrics
            const avgGlicko = playerData.metric_summaries.length > 0 
                ? playerData.metric_summaries.reduce((sum, m) => sum + m.glicko_rating, 0) / playerData.metric_summaries.length
                : 1500;
            
            performanceStats.innerHTML = `
                <div class="stat-row">
                    <span class="stat-label">Average Glicko:</span>
                    <span class="stat-value">${avgGlicko.toFixed(0)}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Best Metric:</span>
                    <span class="stat-value">${bestMetric}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Best Percentile:</span>
                    <span class="stat-value">${bestPercentile.toFixed(1)}%</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Total Metrics:</span>
                    <span class="stat-value">${playerData.metric_summaries.length}</span>
                </div>
            `;
            
            // Activity stats
            const activityStats = document.getElementById('activityStats');
            const firstDate = playerData.profile.first_session;
            const lastDate = playerData.profile.last_session;
            const formattedFirst = `${firstDate.substr(4,2)}/${firstDate.substr(6,2)}/${firstDate.substr(0,4)}`;
            const formattedLast = `${lastDate.substr(4,2)}/${lastDate.substr(6,2)}/${lastDate.substr(0,4)}`;
            
            activityStats.innerHTML = `
                <div class="stat-row">
                    <span class="stat-label">First Session:</span>
                    <span class="stat-value">${formattedFirst}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Latest Session:</span>
                    <span class="stat-value">${formattedLast}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Sessions/Week:</span>
                    <span class="stat-value">${(playerData.profile.total_sessions / (playerData.profile.activity_days / 7)).toFixed(1)}</span>
                </div>
            `;
            
            // Profession-specific metric tables
            loadProfessionMetrics();
            
            // Profession stats
            const professionStats = document.getElementById('professionStats');
            professionStats.innerHTML = `
                <div class="stat-row">
                    <span class="stat-label">Professions Played:</span>
                    <span class="stat-value">${playerData.profile.professions_played.length}</span>
                </div>
                <div class="profession-list">
                    ${playerData.profile.professions_played.map(prof => 
                        `<span class="profession-tag">${prof}</span>`
                    ).join('')}
                </div>
            `;
        }
        
        function switchDateFilter(dateFilter) {
            // Check if data exists for this filter
            if (!allPlayerData[dateFilter]) {
                console.warn(`No data available for ${dateFilter} filter`);
                return;
            }
            
            // Switch to new data
            playerData = allPlayerData[dateFilter];
            currentDateFilter = dateFilter;
            
            // Update UI with new data
            loadPlayerData();
            
            // Update active filter button
            document.querySelectorAll('.date-filter-button').forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.filter === dateFilter) {
                    btn.classList.add('active');
                }
            });
        }
        
        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {
            initializeDarkMode();
            loadPlayerData();
            
            // Dark mode toggle
            document.getElementById('darkModeToggle').addEventListener('click', toggleDarkMode);
            
            // Date filter buttons
            document.querySelectorAll('.date-filter-button').forEach(button => {
                button.addEventListener('click', function() {
                    const filter = this.dataset.filter;
                    if (filter !== currentDateFilter) {
                        switchDateFilter(filter);
                    }
                });
            });
        });
    </script>
</body>
</html>"""
    
    # Generate individual player pages
    for account_name in player_summaries:
        try:
            # Load player data for all date filters
            safe_name = account_name.replace('.', '_').replace(' ', '_')
            all_player_data = {}
            
            # Load data for each date filter
            date_filters = ['overall', '30d', '90d', '180d']
            for date_filter in date_filters:
                try:
                    if date_filter == 'overall':
                        json_file = players_dir / f"{safe_name}.json"
                    else:
                        json_file = players_dir / date_filter / f"{safe_name}_{date_filter}.json"
                    
                    if json_file.exists():
                        with open(json_file, 'r', encoding='utf-8') as f:
                            all_player_data[date_filter] = json.load(f)
                    else:
                        print(f"  Warning: Missing {date_filter} data for {account_name}")
                except Exception as e:
                    print(f"  Warning: Failed to load {date_filter} data for {account_name}: {e}")
            
            # Only generate page if we have at least overall data
            if 'overall' not in all_player_data:
                print(f"  Warning: No overall data for {account_name}, skipping")
                continue
            
            # Generate HTML
            html_content = player_template.replace('{{PLAYER_NAME}}', account_name)
            html_content = html_content.replace('{{ALL_PLAYER_DATA}}', json.dumps(all_player_data))
            
            # Write player page
            html_file = players_dir / f"{safe_name}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
        except Exception as e:
            print(f"  Warning: Failed to generate page for {account_name}: {e}")
            continue
    
    print(f"✅ Generated {len(player_summaries)} player detail pages")


def main():
    parser = argparse.ArgumentParser(description='Generate static web UI for GW2 WvW Leaderboards')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('-o', '--output', default='web_ui', help='Output directory (default: web_ui)')
    parser.add_argument('--skip-recalc', action='store_true', help='Skip recalculating ratings (use existing data)')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers for data generation (default: 4)')

    args = parser.parse_args()

    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1

    output_dir = Path(args.output)

    # Check if glicko_ratings table has data
    conn = sqlite3.connect(args.database)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM glicko_ratings")
    ratings_count = cursor.fetchone()[0]
    conn.close()
    
    if not args.skip_recalc or ratings_count == 0:
        if ratings_count == 0:
            print("Glicko ratings table is empty - forcing recalculation...")
        else:
            print("Recalculating all Glicko ratings...")
        recalculate_all_glicko_ratings(args.database, guild_filter=False)
        print("Rating recalculation complete!")

    print(f"\nGenerating leaderboard data with up to {args.workers} workers...")
    data = generate_all_leaderboard_data(args.database, max_workers=args.workers)

    print("\nGenerating HTML UI...")
    generate_html_ui(data, output_dir)

    # Player summaries now handled by modal in main interface
    # print("\nGenerating player summaries...")
    # player_summaries = generate_player_summaries(args.database, output_dir)
    # 
    # print("\nGenerating player detail pages...")
    # generate_player_detail_pages(output_dir, player_summaries)

    print(f"\n✅ Web UI generation complete!")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print(f"🌐 Open {output_dir / 'index.html'} in your browser to view")
    print(f"📤 Upload the contents of {output_dir} to GitHub Pages or any web host")

    return 0



if __name__ == '__main__':
    exit(main())