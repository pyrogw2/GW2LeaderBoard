"""
Data processing functions for GW2 WvW Leaderboards web UI generation.
Handles database queries, data filtering, and player summary generation.
"""

import json
import sqlite3
import os
import sys
import statistics
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
                ORDER BY g.rating DESC
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
                ORDER BY rating DESC
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
        # For individual metrics, use Glicko rating as both composite score and rating
        # For overall metrics, keep original composite score
        if metric_category and metric_category != "Overall":
            actual_composite_score = rating  # Use Glicko rating for individual metrics
        else:
            actual_composite_score = composite_score  # Use composite score for overall
            
        entry = {
            'rank': i,
            'account_name': account_name,
            'profession': profession,
            'composite_score': actual_composite_score,
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
    """Get leaderboard data with optimized Glicko calculation for date filtering."""
    if not date_filter or date_filter == "overall":
        return get_glicko_leaderboard_data(db_path, metric_category, limit, None, show_deltas)
    
    # Use an optimized approach: calculate Glicko ratings on-demand for the specific metric and date range
    return calculate_glicko_ratings_for_date_filter(db_path, metric_category, date_filter, limit, show_deltas)


def calculate_glicko_ratings_for_date_filter(db_path: str, metric_category: str = None, date_filter: str = None, limit: int = 500, show_deltas: bool = False):
    """Calculate proper Glicko ratings for a specific metric and date range without creating temporary databases."""
    # Import the Glicko system
    try:
        from ..core.glicko_rating_system import GlickoSystem, GlickoRating
    except ImportError:
        from gw2_leaderboard.core.glicko_rating_system import GlickoSystem, GlickoRating
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Build date filter clause
    try:
        days = int(date_filter.rstrip('d'))
        date_clause = f"WHERE parsed_date >= date('now', '-{days} days')"
    except (ValueError, AttributeError):
        conn.close()
        return get_glicko_leaderboard_data(db_path, metric_category, limit, None, show_deltas)
    
    # Check if guild_members table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    
    # Map metric category to database column
    metric_column_map = {
        'DPS': 'target_dps',
        'Healing': 'healing_per_sec', 
        'Barrier': 'barrier_per_sec',
        'Cleanses': 'condition_cleanses_per_sec',
        'Strips': 'boon_strips_per_sec',
        'Stability': 'stability_gen_per_sec',
        'Resistance': 'resistance_gen_per_sec',
        'Might': 'might_gen_per_sec',
        'Protection': 'protection_gen_per_sec',
        'Downs': 'down_contribution_per_sec',
        'Burst Consistency': 'burst_consistency_1s',
        'Distance to Tag': 'distance_from_tag_avg'
    }
    
    if metric_category not in metric_column_map:
        metric_column = 'target_dps'  # Default to DPS
    else:
        metric_column = metric_column_map[metric_category]
    
    # Get all performance data for the date range and metric
    cursor.execute(f'''
        SELECT 
            account_name,
            profession,
            timestamp,
            {metric_column} as metric_value,
            fight_time
        FROM player_performances
        {date_clause}
            AND {metric_column} > 0
            AND fight_time >= 5
        ORDER BY timestamp, account_name
    ''')
    
    performance_data = cursor.fetchall()
    
    if not performance_data:
        conn.close()
        return []
    
    # Group data by session (timestamp) for Glicko calculation
    sessions = {}
    for account_name, profession, timestamp, metric_value, fight_time in performance_data:
        if timestamp not in sessions:
            sessions[timestamp] = []
        sessions[timestamp].append({
            'account_name': account_name,
            'profession': profession,
            'metric_value': metric_value,
            'fight_time': fight_time
        })
    
    # Initialize Glicko system and player ratings
    glicko = GlickoSystem()
    player_ratings = {}  # (account_name, profession) -> GlickoRating
    
    # Process each session to calculate Glicko ratings
    for timestamp in sorted(sessions.keys()):
        session_data = sessions[timestamp]
        
        # Calculate z-scores for this session
        metric_values = [p['metric_value'] for p in session_data]
        if len(metric_values) < 2:
            continue  # Skip sessions with too few players
            
        mean_value = statistics.mean(metric_values)
        try:
            std_value = statistics.stdev(metric_values)
        except statistics.StatisticsError:
            std_value = 1.0  # Avoid division by zero
        
        if std_value == 0:
            std_value = 1.0
        
        # Convert performance to z-scores and then to Glicko outcomes
        session_results = []
        for player in session_data:
            key = (player['account_name'], player['profession'])
            
            # Initialize player rating if new
            if key not in player_ratings:
                player_ratings[key] = GlickoRating(
                    account_name=player['account_name'],
                    profession=player['profession'],
                    metric_category=metric_category or 'Overall'
                )
            
            # Calculate z-score
            z_score = (player['metric_value'] - mean_value) / std_value
            
            session_results.append({
                'key': key,
                'z_score': z_score,
                'metric_value': player['metric_value']
            })
        
        # Update Glicko ratings based on session results
        # Sort by z-score to create pairwise comparisons
        session_results.sort(key=lambda x: x['z_score'], reverse=True)
        
        # Update Glicko ratings for each player using their z-score from this session
        for player_result in session_results:
            key = player_result['key']
            z_score = player_result['z_score']
            rating = player_ratings[key]
            
            # Update rating using the z-score from this session
            new_rating, new_rd, new_volatility = glicko.update_rating(
                rating.rating, rating.rd, rating.volatility, [z_score]
            )
            
            # Update the rating object
            rating.rating = new_rating
            rating.rd = new_rd
            rating.volatility = new_volatility
            rating.games_played += 1
    
    # Convert to leaderboard format
    leaderboard_data = []
    for (account_name, profession), rating in player_ratings.items():
        # Calculate additional stats including average rank percentile
        cursor.execute(f'''
            SELECT 
                COUNT(*) as games_played,
                AVG({metric_column}) as avg_stat_value
            FROM player_performances
            {date_clause}
                AND account_name = ?
                AND profession = ?
                AND {metric_column} > 0
                AND fight_time >= 5
        ''', (account_name, profession))
        
        result = cursor.fetchone()
        if result:
            games_played, avg_stat_value = result
            
            # Calculate average rank position across sessions (1st, 2nd, 3rd, etc.)
            avg_rank_percent = 25.0  # Default (roughly middle rank for typical squad size)
            if games_played > 0:
                cursor.execute(f'''
                    WITH session_stats AS (
                        SELECT 
                            p.timestamp,
                            p.account_name,
                            p.profession,
                            p.{metric_column} as player_value,
                            COUNT(*) OVER (PARTITION BY p.timestamp) as session_size,
                            RANK() OVER (PARTITION BY p.timestamp ORDER BY {metric_column} DESC) as player_rank
                        FROM player_performances p
                        WHERE p.timestamp IN (
                            SELECT DISTINCT timestamp 
                            FROM player_performances 
                            {date_clause}
                                AND account_name = ?
                                AND profession = ?
                                AND {metric_column} > 0
                                AND fight_time >= 5
                        )
                        AND p.{metric_column} > 0
                        AND p.fight_time >= 5
                    )
                    SELECT AVG(player_rank) as avg_rank_position
                    FROM session_stats ss
                    WHERE ss.account_name = ? AND ss.profession = ?
                ''', (account_name, profession, account_name, profession))
                
                rank_result = cursor.fetchone()
                if rank_result and rank_result[0] is not None:
                    avg_rank_percent = rank_result[0]
            
            # Check guild membership
            is_guild_member = False
            if guild_table_exists:
                cursor.execute("SELECT 1 FROM guild_members WHERE account_name = ?", (account_name,))
                is_guild_member = cursor.fetchone() is not None
            
            leaderboard_data.append({
                'account_name': account_name,
                'profession': profession,
                'glicko_rating': rating.rating,
                'composite_score': rating.rating,  # Use Glicko rating as composite score
                'games_played': games_played,
                'average_rank_percent': avg_rank_percent,
                'average_stat_value': avg_stat_value or 0,
                'is_guild_member': is_guild_member,
                'rating_delta': 0.0  # Will be calculated after all data is processed
            })
    
    # Sort by Glicko rating and add ranks
    leaderboard_data.sort(key=lambda x: x['glicko_rating'], reverse=True)
    for i, player in enumerate(leaderboard_data[:limit], 1):
        player['rank'] = i
    
    # Calculate rating deltas from history if available
    try:
        # Import rating history functions
        try:
            from ..core.rating_history import calculate_rating_deltas_from_history
        except ImportError:
            from gw2_leaderboard.core.rating_history import calculate_rating_deltas_from_history
        
        # Get all rating deltas for this metric
        all_deltas = calculate_rating_deltas_from_history(db_path, metric_category or "Overall")
        
        # Apply deltas to players
        for player in leaderboard_data[:limit]:
            delta_key = (player['account_name'], player['profession'], metric_category or "Overall")
            player['rating_delta'] = all_deltas.get(delta_key, 0.0)
            
    except Exception as e:
        print(f"    Warning: Could not calculate rating deltas: {e}")
        # Rating deltas remain 0.0
    
    conn.close()
    return leaderboard_data[:limit]


def get_glicko_leaderboard_data_fast_approximation(db_path: str, metric_category: str = None, date_filter: str = None, limit: int = 500, show_deltas: bool = False):
    """Fast approximation when proper Glicko calculation is not available."""
    # Original fast approximation code as backup
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Build date filter clause
    try:
        days = int(date_filter.rstrip('d'))
        date_clause = f"WHERE parsed_date >= date('now', '-{days} days')"
    except (ValueError, AttributeError):
        conn.close()
        return get_glicko_leaderboard_data(db_path, metric_category, limit, None, show_deltas)
    
    # Check if guild_members table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    
    # Map metric category to database column
    metric_column_map = {
        'DPS': 'target_dps',
        'Healing': 'healing_per_sec', 
        'Barrier': 'barrier_per_sec',
        'Cleanses': 'condition_cleanses_per_sec',
        'Strips': 'boon_strips_per_sec',
        'Stability': 'stability_gen_per_sec',
        'Resistance': 'resistance_gen_per_sec',
        'Might': 'might_gen_per_sec',
        'Protection': 'protection_gen_per_sec',
        'Downs': 'down_contribution_per_sec',
        'Burst Consistency': 'burst_consistency_1s',
        'Distance to Tag': 'distance_from_tag_avg'
    }
    
    if metric_category and metric_category in metric_column_map:
        metric_column = metric_column_map[metric_category]
        
        # Calculate basic statistics for each player from their date-filtered performances
        if guild_table_exists:
            cursor.execute(f'''
                SELECT 
                    p.account_name,
                    p.profession,
                    COUNT(*) as games_played,
                    AVG({metric_column}) as avg_stat_value,
                    50.0 as avg_rank_percent,
                    CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM player_performances p
                LEFT JOIN guild_members gm ON p.account_name = gm.account_name
                {date_clause}
                    AND {metric_column} > 0
                    AND fight_time >= 5
                GROUP BY p.account_name, p.profession, gm.account_name
                HAVING COUNT(*) >= 3
                ORDER BY avg_stat_value DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute(f'''
                SELECT 
                    account_name,
                    profession,
                    COUNT(*) as games_played,
                    AVG({metric_column}) as avg_stat_value,
                    50.0 as avg_rank_percent,
                    0 as is_guild_member
                FROM player_performances
                {date_clause}
                    AND {metric_column} > 0
                    AND fight_time >= 5
                GROUP BY account_name, profession
                HAVING COUNT(*) >= 3
                ORDER BY avg_stat_value DESC
                LIMIT ?
            ''', (limit,))
    else:
        # For "Overall" or unknown categories, use DPS as fallback
        metric_column = 'target_dps'
        
        if guild_table_exists:
            cursor.execute(f'''
                SELECT 
                    p.account_name,
                    p.profession,
                    COUNT(*) as games_played,
                    AVG({metric_column}) as avg_stat_value,
                    50.0 as avg_rank_percent,
                    CASE WHEN gm.account_name IS NOT NULL THEN 1 ELSE 0 END as is_guild_member
                FROM player_performances p
                LEFT JOIN guild_members gm ON p.account_name = gm.account_name
                {date_clause}
                    AND {metric_column} > 0
                    AND fight_time >= 5
                GROUP BY p.account_name, p.profession, gm.account_name
                HAVING COUNT(*) >= 3
                ORDER BY avg_stat_value DESC
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute(f'''
                SELECT 
                    account_name,
                    profession,
                    COUNT(*) as games_played,
                    AVG({metric_column}) as avg_stat_value,
                    50.0 as avg_rank_percent,
                    0 as is_guild_member
                FROM player_performances
                {date_clause}
                    AND {metric_column} > 0
                    AND fight_time >= 5
                GROUP BY account_name, profession
                HAVING COUNT(*) >= 3
                ORDER BY avg_stat_value DESC
                LIMIT ?
            ''', (limit,))
    
    leaderboard_data = []
    for i, row in enumerate(cursor.fetchall(), 1):
        # Create simplified rating based on average performance for speed
        avg_stat = row[3] if row[3] is not None else 0
        games_played = row[2]
        avg_rank_percent = row[4] if row[4] is not None else 50.0
        
        # Calculate proper Glicko-style rating using performance data
        normalized_stat = avg_stat / 1000.0  # Adjust scale
        
        # Base Glicko rating calculation
        base_rating = 1500.0
        performance_factor = normalized_stat * 50  # Scale factor for metric influence
        experience_bonus = min(50, games_played * 3)  # Up to 50 points for experience
        consistency_factor = max(0.5, (100 - avg_rank_percent) / 200)  # Rank consistency
        
        # Calculate rating using Glicko-style approach
        glicko_rating = base_rating + (performance_factor * consistency_factor) + experience_bonus
        
        # Calculate composite score for sorting (should be close to Glicko rating)
        composite_score = glicko_rating
        
        player_data = {
            "rank": i,
            "account_name": row[0],
            "profession": row[1],
            "composite_score": composite_score,
            "glicko_rating": glicko_rating,
            "games_played": games_played,
            "average_rank_percent": avg_rank_percent,
            "average_stat_value": avg_stat,
            "is_guild_member": bool(row[5]),
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