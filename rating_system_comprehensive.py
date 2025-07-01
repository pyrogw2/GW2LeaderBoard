#!/usr/bin/env python3
"""
Comprehensive multi-category ELO rating system for GW2 leaderboard.
Handles 8 separate metric categories with session-based comparisons.
Tracks each player+profession combination separately but shows unified leaderboards.
"""

import sqlite3
import math
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class PlayerRating:
    account_name: str
    profession: str
    metric_category: str
    elo_rating: float = 1200.0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0


class EloRatingSystem:
    """ELO rating system implementation for GW2 metrics."""
    
    def __init__(self, k_factor: int = 32):
        self.k_factor = k_factor
    
    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for player A against player B."""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
    
    def update_ratings(self, rating_a: float, rating_b: float, score_a: float) -> Tuple[float, float]:
        """
        Update ratings based on match result.
        score_a: 1.0 for win, 0.5 for draw, 0.0 for loss
        """
        expected_a = self.expected_score(rating_a, rating_b)
        expected_b = self.expected_score(rating_b, rating_a)
        
        new_rating_a = rating_a + self.k_factor * (score_a - expected_a)
        new_rating_b = rating_b + self.k_factor * ((1.0 - score_a) - expected_b)
        
        return new_rating_a, new_rating_b


# Define metric categories and their database column names
METRIC_CATEGORIES = {
    'DPS': 'target_dps',
    'Healing': 'healing_per_sec',
    'Barrier': 'barrier_per_sec',
    'Cleanses': 'condition_cleanses_per_sec',
    'Strips': 'boon_strips_per_sec',
    'Stability': 'stability_gen_per_sec',
    'Resistance': 'resistance_gen_per_sec',
    'Might': 'might_gen_per_sec'
}


def get_session_rankings(db_path: str, timestamp: str, metric_category: str) -> List[Dict]:
    """Get player rankings for a specific metric in a specific session."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    metric_column = METRIC_CATEGORIES[metric_category]
    
    query = f'''
        SELECT account_name, profession, {metric_column}, fight_time
        FROM player_performances 
        WHERE timestamp = ? AND {metric_column} > 0
        ORDER BY {metric_column} DESC
    '''
    
    cursor.execute(query, (timestamp,))
    results = cursor.fetchall()
    conn.close()
    
    rankings = []
    for i, (account_name, profession, metric_value, fight_time) in enumerate(results):
        rankings.append({
            'account_name': account_name,
            'profession': profession,
            'metric_value': metric_value,
            'fight_time': fight_time,
            'rank': i + 1,
            'total_players': len(results)
        })
    
    return rankings


def determine_performance_score(rank: int, total_players: int) -> float:
    """
    Determine performance score based on rank within session.
    Top 25% = win (1.0), bottom 25% = loss (0.0), middle 50% = draw (0.5)
    """
    if total_players < 2:
        return 0.5  # Can't determine performance with fewer than 2 players
    
    rank_percentile = rank / total_players
    
    if rank_percentile <= 0.25:  # Top 25%
        return 1.0
    elif rank_percentile >= 0.75:  # Bottom 25%
        return 0.0
    else:  # Middle 50%
        return 0.5


def get_current_rating(db_path: str, account_name: str, profession: str, metric_category: str) -> Tuple[float, int, int, int, int]:
    """Get current ELO rating and stats for a player+profession+metric combination."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT elo_rating, games_played, wins, losses, draws
        FROM player_ratings 
        WHERE account_name = ? AND profession = ? AND metric_category = ?
    ''', (account_name, profession, metric_category))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0], result[1], result[2], result[3], result[4]
    else:
        return 1200.0, 0, 0, 0, 0  # Default values


def update_player_rating(db_path: str, account_name: str, profession: str, metric_category: str,
                        new_rating: float, games_played: int, wins: int, losses: int, draws: int):
    """Update player rating in database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO player_ratings 
        (account_name, profession, metric_category, elo_rating, games_played, wins, losses, draws)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (account_name, profession, metric_category, new_rating, games_played, wins, losses, draws))
    
    conn.commit()
    conn.close()


def calculate_ratings_for_session(db_path: str, timestamp: str):
    """Calculate rating changes for all players in a session across all metric categories."""
    elo_system = EloRatingSystem()
    
    for metric_category in METRIC_CATEGORIES.keys():
        print(f"  Processing {metric_category} ratings...")
        
        # Get rankings for this metric in this session
        rankings = get_session_rankings(db_path, timestamp, metric_category)
        
        if len(rankings) < 2:
            continue  # Need at least 2 players for meaningful comparisons
        
        # Update ratings for each player+profession combination
        for player in rankings:
            account_name = player['account_name']
            profession = player['profession']
            rank = player['rank']
            total_players = player['total_players']
            
            # Get current rating for this specific account+profession+metric combo
            current_rating, games, wins, losses, draws = get_current_rating(
                db_path, account_name, profession, metric_category)
            
            # Determine performance score
            performance_score = determine_performance_score(rank, total_players)
            
            # Update game stats
            games += 1
            if performance_score > 0.5:
                wins += 1
            elif performance_score < 0.5:
                losses += 1
            else:
                draws += 1
            
            # Calculate new rating against session average
            session_avg_rating = 1200.0  # Could calculate actual session average
            new_rating, _ = elo_system.update_ratings(
                current_rating, session_avg_rating, performance_score)
            
            # Store updated rating for this account+profession+metric combination
            update_player_rating(db_path, account_name, profession, metric_category,
                                new_rating, games, wins, losses, draws)


def recalculate_all_ratings(db_path: str):
    """Recalculate all ratings chronologically across all metric categories."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing ratings
    cursor.execute('DELETE FROM player_ratings')
    conn.commit()
    
    # Get all timestamps in chronological order
    cursor.execute('SELECT DISTINCT timestamp FROM player_performances ORDER BY timestamp')
    timestamps = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    print(f"Recalculating ratings for {len(timestamps)} sessions across {len(METRIC_CATEGORIES)} metrics...")
    
    for i, timestamp in enumerate(timestamps):
        print(f"Processing session {i+1}/{len(timestamps)}: {timestamp}")
        calculate_ratings_for_session(db_path, timestamp)


def show_leaderboard(db_path: str, metric_category: str = None, limit: int = 20):
    """Show leaderboard for a specific metric category (all professions combined)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if metric_category:
        if metric_category not in METRIC_CATEGORIES:
            print(f"Invalid metric category. Choose from: {list(METRIC_CATEGORIES.keys())}")
            return
        
        query = '''
            SELECT account_name, profession, elo_rating, games_played, wins, losses, draws
            FROM player_ratings 
            WHERE metric_category = ?
            ORDER BY elo_rating DESC
            LIMIT ?
        '''
        cursor.execute(query, (metric_category, limit))
        results = cursor.fetchall()
        
        print(f"\n=== {metric_category} Leaderboard ===")
        print(f"{'Rank':<4} {'Account':<25} {'Profession':<15} {'ELO':<6} {'Games':<6} {'W/L/D':<8} {'Win%':<6}")
        print("-" * 85)
        
        for i, row in enumerate(results, 1):
            account, prof, elo, games, wins, losses, draws = row
            wld = f"{wins}/{losses}/{draws}"
            win_rate = (wins / games * 100) if games > 0 else 0
            print(f"{i:<4} {account:<25} {prof:<15} {elo:<6.0f} {games:<6} {wld:<8} {win_rate:<6.1f}%")
    else:
        # Show top players across all categories
        query = '''
            SELECT account_name, profession, metric_category, elo_rating, games_played, wins, losses, draws
            FROM player_ratings 
            ORDER BY elo_rating DESC
            LIMIT ?
        '''
        cursor.execute(query, (limit,))
        results = cursor.fetchall()
        
        print(f"\n=== Overall Top Performers (All Categories) ===")
        print(f"{'Rank':<4} {'Account':<25} {'Profession':<15} {'Category':<10} {'ELO':<6} {'Games':<6} {'W/L/D':<8}")
        print("-" * 95)
        
        for i, row in enumerate(results, 1):
            account, prof, category, elo, games, wins, losses, draws = row
            wld = f"{wins}/{losses}/{draws}"
            print(f"{i:<4} {account:<25} {prof:<15} {category:<10} {elo:<6.0f} {games:<6} {wld:<8}")
    
    conn.close()


def show_player_profile(db_path: str, account_name: str):
    """Show comprehensive profile for a specific player across all their profession+metric combinations."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all ratings for this player
    cursor.execute('''
        SELECT profession, metric_category, elo_rating, games_played, wins, losses, draws
        FROM player_ratings 
        WHERE account_name = ?
        ORDER BY profession, metric_category
    ''', (account_name,))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"No rating data found for player: {account_name}")
        return
    
    print(f"\n=== Player Profile: {account_name} ===")
    print(f"{'Profession':<15} {'Category':<10} {'ELO':<6} {'Games':<6} {'W/L/D':<8} {'Win%':<6}")
    print("-" * 70)
    
    for prof, category, elo, games, wins, losses, draws in results:
        wld = f"{wins}/{losses}/{draws}"
        win_rate = (wins / games * 100) if games > 0 else 0
        print(f"{prof:<15} {category:<10} {elo:<6.0f} {games:<6} {wld:<8} {win_rate:<6.1f}%")
    
    # Show performance summary
    cursor.execute('''
        SELECT COUNT(DISTINCT profession) as professions,
               COUNT(DISTINCT metric_category) as categories,
               AVG(elo_rating) as avg_elo,
               SUM(games_played) as total_games
        FROM player_ratings 
        WHERE account_name = ?
    ''', (account_name,))
    
    summary = cursor.fetchone()
    if summary:
        print(f"\nSummary: {summary[0]} professions, {summary[1]} categories, {summary[2]:.0f} avg ELO, {summary[3]} total games")
    
    conn.close()


def show_category_summary(db_path: str):
    """Show summary statistics for each metric category."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"\n=== Category Summary ===")
    print(f"{'Category':<10} {'Entries':<8} {'Players':<8} {'Games':<8} {'Avg ELO':<8} {'Top ELO':<8}")
    print("-" * 60)
    
    for category in METRIC_CATEGORIES.keys():
        cursor.execute('''
            SELECT COUNT(*) as entries,
                   COUNT(DISTINCT account_name) as players,
                   SUM(games_played) as total_games,
                   AVG(elo_rating) as avg_elo,
                   MAX(elo_rating) as max_elo
            FROM player_ratings 
            WHERE metric_category = ?
        ''', (category,))
        
        result = cursor.fetchone()
        if result and result[0] > 0:
            entries, players, games, avg_elo, max_elo = result
            print(f"{category:<10} {entries:<8} {players:<8} {games:<8} {avg_elo:<8.0f} {max_elo:<8.0f}")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Comprehensive GW2 Rating System')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('--recalculate', action='store_true', help='Recalculate all ratings')
    parser.add_argument('--leaderboard', help='Show leaderboard for specific category')
    parser.add_argument('--all-leaderboards', action='store_true', help='Show leaderboards for all categories')
    parser.add_argument('--player', help='Show profile for specific player')
    parser.add_argument('--summary', action='store_true', help='Show category summary statistics')
    parser.add_argument('--limit', type=int, default=20, help='Number of entries to show')
    
    args = parser.parse_args()
    
    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1
    
    if args.recalculate:
        recalculate_all_ratings(args.database)
        print("Rating recalculation complete!")
    
    if args.leaderboard:
        show_leaderboard(args.database, args.leaderboard, args.limit)
    
    if args.all_leaderboards:
        for category in METRIC_CATEGORIES.keys():
            show_leaderboard(args.database, category, args.limit)
    
    if args.player:
        show_player_profile(args.database, args.player)
    
    if args.summary:
        show_category_summary(args.database)
    
    return 0


if __name__ == '__main__':
    exit(main())