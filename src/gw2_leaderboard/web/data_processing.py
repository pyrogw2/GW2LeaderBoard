"""
Data processing functions for GW2 WvW Leaderboards web UI generation.
Handles database queries, data filtering, and player summary generation.
"""

import json
import sqlite3
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory and parent directories to Python path to import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
sys.path.extend([current_dir, parent_dir, grandparent_dir])

# Handle both relative and absolute imports
try:
    from ..core.glicko_rating_system import (
        PROFESSION_METRICS,
        recalculate_profession_ratings,
        calculate_date_filtered_ratings,
        calculate_simple_profession_ratings
    )
    from ..core.rating_history import calculate_rating_deltas_from_history, get_player_rating_history
except ImportError:
    # Fall back to absolute imports for standalone execution
    from gw2_leaderboard.core.glicko_rating_system import (
        PROFESSION_METRICS,
        recalculate_profession_ratings,
        calculate_date_filtered_ratings,
        calculate_simple_profession_ratings
    )
    from gw2_leaderboard.core.rating_history import calculate_rating_deltas_from_history, get_player_rating_history

# Optional guild manager import
try:
    from guild_manager import GuildManager
    GUILD_MANAGER_AVAILABLE = True
except ImportError:
    GUILD_MANAGER_AVAILABLE = False
    GuildManager = None

# Optional player summary import
try:
    from ..core.player_summary import PlayerSummaryGenerator
    PLAYER_SUMMARY_AVAILABLE = True
except ImportError:
    try:
        from gw2_leaderboard.core.player_summary import PlayerSummaryGenerator
        PLAYER_SUMMARY_AVAILABLE = True
    except ImportError:
        PLAYER_SUMMARY_AVAILABLE = False
        PlayerSummaryGenerator = None


def recalculate_all_glicko_ratings(db_path: str, guild_filter: bool = False):
    """Recalculate Glicko ratings for all professions and metrics."""
    print("Recalculating ratings for all professions...")
    
    # Get all available professions
    professions = list(PROFESSION_METRICS.keys())
    
    # Add special professions that might not be in PROFESSION_METRICS
    additional_professions = ["Condi Firebrand", "Support Spb"]
    for prof in additional_professions:
        if prof not in professions:
            professions.append(prof)
    
    for i, profession in enumerate(professions, 1):
        print(f"  ({i}/{len(professions)}) Recalculating {profession}...")
        try:
            recalculate_profession_ratings(db_path, profession, guild_filter=guild_filter)
        except Exception as e:
            print(f"    Warning: Failed to recalculate {profession}: {e}")
            continue
    
    print("✅ All profession ratings recalculated")


def get_glicko_leaderboard_data(db_path: str, metric_category: str = None, limit: int = 500, date_filter: str = None, show_deltas: bool = False):
    """Extract leaderboard data from database with guild membership info."""
    
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
            # Add special filter for Distance to Tag to exclude N/A distance with only 1 raid
            where_clause = "WHERE g.metric_category = ?"
            if metric_category == "Distance to Tag":
                where_clause += " AND NOT (g.average_stat_value = 0 AND g.games_played = 1)"
            
            cursor.execute(f'''
                SELECT g.account_name, g.profession, g.composite_score, g.rating, g.games_played, 
                       g.average_rank, g.average_stat_value,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM glicko_ratings g
                LEFT JOIN guild_members gm ON g.account_name = gm.account_name
                {where_clause}
                ORDER BY g.composite_score DESC
                LIMIT ?
            ''', (metric_category, limit))
        else:
            # Add special filter for Distance to Tag to exclude N/A distance with only 1 raid
            where_clause = "WHERE metric_category = ?"
            if metric_category == "Distance to Tag":
                where_clause += " AND NOT (average_stat_value = 0 AND games_played = 1)"
            
            cursor.execute(f'''
                SELECT account_name, profession, composite_score, rating, games_played, 
                       average_rank, average_stat_value, 0 as is_guild_member
                FROM glicko_ratings
                {where_clause}
                ORDER BY composite_score DESC
                LIMIT ?
            ''', (metric_category, limit))
    else:
        # Overall leaderboard with guild membership info
        if guild_table_exists:
            cursor.execute('''
                SELECT g.account_name, g.profession, g.composite_score, g.rating, g.games_played, 
                       g.average_rank, g.average_stat_value,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM glicko_ratings g
                LEFT JOIN guild_members gm ON g.account_name = gm.account_name
                WHERE g.metric_category = 'Overall'
                ORDER BY g.composite_score DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT account_name, profession, composite_score, rating, games_played, 
                       average_rank, average_stat_value, 0 as is_guild_member
                FROM glicko_ratings
                WHERE metric_category = 'Overall'
                ORDER BY composite_score DESC
                LIMIT ?
            ''', (limit,))
    
    results = cursor.fetchall()
    
    leaderboard_data = []
    for i, (account_name, profession, composite_score, rating, games_played, average_rank, average_stat_value, is_guild_member) in enumerate(results, 1):
        entry = {
            'rank': i,
            'account_name': account_name,
            'profession': profession,
            'composite_score': composite_score,
            'glicko_rating': rating,
            'games_played': games_played,
            'average_rank_percent': average_rank,
            'average_stat_value': average_stat_value,
            'is_guild_member': bool(is_guild_member)
        }
        
        # Add rating delta if requested
        if show_deltas:
            # Get rating delta from history
            all_deltas = calculate_rating_deltas_from_history(db_path, metric_category or "Overall")
            delta_key = (account_name, profession, metric_category or "Overall")
            entry['rating_delta'] = all_deltas.get(delta_key, 0.0)
        
        leaderboard_data.append(entry)
    
    conn.close()
    return leaderboard_data


def get_glicko_leaderboard_data_with_sql_filter(db_path: str, metric_category: str = None, date_filter: str = None, limit: int = 500, show_deltas: bool = False):
    """Get leaderboard data with SQL-level date filtering for maximum speed."""
    if not date_filter or date_filter == "overall":
        return get_glicko_leaderboard_data(db_path, metric_category, limit, None, show_deltas)
    
    # For speed, we'll use a fast approximation: 
    # Apply simple date-based filtering to the existing ratings
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Build date filter clause
    try:
        days = int(date_filter.rstrip('d'))
        date_clause = f" AND pp.parsed_date >= date('now', '-{days} days')"
    except (ValueError, AttributeError):
        # If date filter is invalid, return overall data
        conn.close()
        return get_glicko_leaderboard_data(db_path, metric_category, limit, None, show_deltas)
    
    # Check if guild_members table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    
    if metric_category and metric_category != "Overall":
        # Get players who have recent activity in the specified time period
        if guild_table_exists:
            where_clause = f"WHERE g.metric_category = ? AND EXISTS (SELECT 1 FROM player_performances pp WHERE pp.account_name = g.account_name{date_clause})"
            
            cursor.execute(f'''
                SELECT g.account_name, g.profession, g.composite_score, g.rating, g.games_played, 
                       g.average_rank, g.average_stat_value,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM glicko_ratings g
                LEFT JOIN guild_members gm ON g.account_name = gm.account_name
                {where_clause}
                ORDER BY g.composite_score DESC
                LIMIT ?
            ''', (metric_category, limit))
        else:
            where_clause = f"WHERE g.metric_category = ? AND EXISTS (SELECT 1 FROM player_performances pp WHERE pp.account_name = g.account_name{date_clause})"
            
            cursor.execute(f'''
                SELECT account_name, profession, composite_score, rating, games_played, 
                       average_rank, average_stat_value, 0 as is_guild_member
                FROM glicko_ratings g
                {where_clause}
                ORDER BY composite_score DESC
                LIMIT ?
            ''', (metric_category, limit))
    else:
        # Overall category - similar filtering
        if guild_table_exists:
            where_clause = f"WHERE g.metric_category = 'Overall' AND EXISTS (SELECT 1 FROM player_performances pp WHERE pp.account_name = g.account_name{date_clause})"
            
            cursor.execute(f'''
                SELECT g.account_name, g.profession, g.composite_score, g.rating, g.games_played, 
                       g.average_rank, g.average_stat_value,
                       CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM glicko_ratings g
                LEFT JOIN guild_members gm ON g.account_name = gm.account_name
                {where_clause}
                ORDER BY g.composite_score DESC
                LIMIT ?
            ''', (limit,))
        else:
            where_clause = f"WHERE g.metric_category = 'Overall' AND EXISTS (SELECT 1 FROM player_performances pp WHERE pp.account_name = g.account_name{date_clause})"
            
            cursor.execute(f'''
                SELECT account_name, profession, composite_score, rating, games_played, 
                       average_rank, average_stat_value, 0 as is_guild_member
                FROM glicko_ratings g
                {where_clause}
                ORDER BY composite_score DESC
                LIMIT ?
            ''', (limit,))
    
    leaderboard_data = []
    for row in cursor.fetchall():
        rank = len(leaderboard_data) + 1
        
        player_data = {
            "rank": rank,
            "account_name": row[0],
            "profession": row[1],
            "composite_score": row[2],
            "glicko_rating": row[3],
            "games_played": row[4],
            "average_rank_percent": row[5],
            "average_stat_value": row[6],
            "is_guild_member": bool(row[7]),
            "rating_delta": 0.0  # TODO: Calculate deltas for date-filtered data
        }
        leaderboard_data.append(player_data)
    
    conn.close()
    return leaderboard_data

def get_filtered_leaderboard_data(db_path: str, metric_category: str = None, limit: int = 500, date_filter: str = None, show_deltas: bool = False):
    """Get leaderboard data filtered by date. This function is now handled by pre-filtering in parallel_processing."""
    # Since we pre-filter databases in parallel_processing.py, this just calls the main function
    return get_glicko_leaderboard_data(db_path, metric_category, limit, None, show_deltas)


def get_new_high_scores_data(db_path: str, limit: int = 100) -> Dict[str, List[Dict]]:
    """Get high scores data from the new high_scores table."""
    return get_high_scores_data(db_path, limit)


def get_high_scores_data(db_path: str, limit: int = 100) -> Dict[str, List[Dict]]:
    """Get top burst damage records for High Scores section."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if guild_members table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    
    high_scores_data = {}
    
    # Get highest 1-second burst damage
    if guild_table_exists:
        cursor.execute('''
            SELECT p.account_name, p.profession, p.burst_consistency_1s, p.timestamp,
                   CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
            FROM player_performances p
            LEFT JOIN guild_members gm ON p.account_name = gm.account_name
            WHERE p.burst_consistency_1s > 0
            ORDER BY p.burst_consistency_1s DESC
            LIMIT ?
        ''', (limit,))
    else:
        cursor.execute('''
            SELECT account_name, profession, burst_consistency_1s, timestamp, 0 as is_guild_member
            FROM player_performances
            WHERE burst_consistency_1s > 0
            ORDER BY burst_consistency_1s DESC
            LIMIT ?
        ''', (limit,))
    
    results = cursor.fetchall()
    burst_scores = []
    
    for i, (account_name, profession, burst_damage, timestamp, is_guild_member) in enumerate(results, 1):
        burst_scores.append({
            'rank': i,
            'account_name': account_name,
            'profession': profession,
            'burst_damage': burst_damage,
            'timestamp': timestamp,
            'is_guild_member': bool(is_guild_member)
        })
    
    high_scores_data['Highest 1 Sec Burst'] = burst_scores
    
    conn.close()
    return high_scores_data


def get_most_played_professions_data(db_path: str, limit: int = 500) -> List[Dict]:
    """Get most played professions data for Player Stats section."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if guild_members table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    
    # Get profession play statistics per player
    if guild_table_exists:
        cursor.execute('''
            SELECT p.account_name, p.profession, COUNT(*) as session_count,
                   CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
            FROM player_performances p
            LEFT JOIN guild_members gm ON p.account_name = gm.account_name
            GROUP BY p.account_name, p.profession, gm.account_name
            ORDER BY p.account_name, session_count DESC
        ''')
    else:
        cursor.execute('''
            SELECT account_name, profession, COUNT(*) as session_count, 0 as is_guild_member
            FROM player_performances
            GROUP BY account_name, profession
            ORDER BY account_name, session_count DESC
        ''')
    
    results = cursor.fetchall()
    
    # Group by player
    player_data = {}
    for account_name, profession, session_count, is_guild_member in results:
        if account_name not in player_data:
            player_data[account_name] = {
                'account_name': account_name,
                'professions': [],
                'total_sessions': 0,
                'is_guild_member': bool(is_guild_member)
            }
        
        player_data[account_name]['professions'].append({
            'profession': profession,
            'session_count': session_count
        })
        player_data[account_name]['total_sessions'] += session_count
    
    # Convert to list and sort by total sessions
    player_list = []
    for account_name, data in player_data.items():
        # Sort professions by session count
        data['professions'].sort(key=lambda x: x['session_count'], reverse=True)
        
        # Set primary profession (most played)
        data['primary_profession'] = data['professions'][0]['profession'] if data['professions'] else 'Unknown'
        data['profession_count'] = len(data['professions'])
        
        # Convert professions list to the format expected by the profession bar formatter
        data['professions_played'] = data['professions']
        
        player_list.append(data)
    
    # Sort by total sessions descending
    player_list.sort(key=lambda x: x['total_sessions'], reverse=True)
    
    # Add ranks and limit results
    limited_list = player_list[:limit]
    for i, player in enumerate(limited_list, 1):
        player['rank'] = i
    
    conn.close()
    return limited_list


def generate_player_summaries_for_filter(db_path: str, date_filter: str, output_dir: Path) -> Dict[str, Any]:
    """Generate player summaries for a specific date filter."""
    if not PLAYER_SUMMARY_AVAILABLE:
        print(f"  Skipping player summaries for {date_filter}: PlayerSummaryGenerator not available")
        return {}
    
    print(f"  Generating player summaries for {date_filter}...")
    generator = PlayerSummaryGenerator(db_path)
    
    try:
        # Generate summaries with date filtering
        if date_filter == 'overall':
            summaries = generator.generate_summaries(limit=None)
        else:
            # Extract days from filter (e.g., "30d" -> 30)
            days = int(date_filter.rstrip('d'))
            summaries = generator.generate_summaries(limit=None, days_filter=days)
        
        # Save summaries to individual JSON files
        player_summaries_dir = output_dir / f"player_summaries_{date_filter}"
        player_summaries_dir.mkdir(exist_ok=True)
        
        # Write individual player files
        for account_name, summary in summaries.items():
            # Clean account name for filename
            safe_name = "".join(c for c in account_name if c.isalnum() or c in "._-")
            file_path = player_summaries_dir / f"{safe_name}.json"
            
            with open(file_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
        
        print(f"    Generated {len(summaries)} player summaries for {date_filter}")
        return summaries
        
    except Exception as e:
        print(f"    Error generating player summaries for {date_filter}: {e}")
        return {}


def generate_player_summaries(db_path: str, output_dir: Path, date_filters: List[str]) -> Dict[str, Dict[str, Any]]:
    """Generate player summary JSON files for all active players."""
    if not PLAYER_SUMMARY_AVAILABLE:
        print("Skipping player summaries: PlayerSummaryGenerator not available")
        return {}
    
    print("Generating player summaries...")
    
    all_summaries = {}
    
    # Use threading to generate summaries for different date filters in parallel
    def process_filter(date_filter):
        try:
            summaries = generate_player_summaries_for_filter(db_path, date_filter, output_dir)
            return date_filter, summaries
        except Exception as e:
            print(f"    Error processing {date_filter}: {e}")
            return date_filter, {}
    
    # Process filters concurrently
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_filter = {executor.submit(process_filter, date_filter): date_filter 
                           for date_filter in date_filters}
        
        for future in as_completed(future_to_filter):
            date_filter = future_to_filter[future]
            try:
                filter_name, summaries = future.result()
                all_summaries[filter_name] = summaries
            except Exception as e:
                print(f"    Failed to process {date_filter}: {e}")
                all_summaries[date_filter] = {}
    
    print(f"✅ Player summaries complete")
    return all_summaries