#!/usr/bin/env python3
"""
ELO and Glicko rating system for GW2 leaderboard.
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
    role: str
    elo_rating: float = 1200.0
    glicko_rating: float = 1500.0
    glicko_rd: float = 200.0  # Rating deviation
    games_played: int = 0
    wins: int = 0
    losses: int = 0


class EloRatingSystem:
    """Simple ELO rating system implementation."""
    
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


class GlickoRatingSystem:
    """Glicko rating system implementation (simplified)."""
    
    def __init__(self, initial_rating: float = 1500.0, initial_rd: float = 200.0):
        self.initial_rating = initial_rating
        self.initial_rd = initial_rd
        self.c = 15.8  # Rating volatility constant
    
    def g(self, rd: float) -> float:
        """Calculate g(RD) function."""
        return 1.0 / math.sqrt(1.0 + 3.0 * (rd * rd) / (math.pi * math.pi))
    
    def expected_score(self, rating: float, opponent_rating: float, opponent_rd: float) -> float:
        """Calculate expected score against opponent."""
        return 1.0 / (1.0 + 10.0 ** (-self.g(opponent_rd) * (rating - opponent_rating) / 400.0))
    
    def update_rating(self, rating: float, rd: float, opponents: List[Tuple[float, float, float]]) -> Tuple[float, float]:
        """
        Update rating and RD based on results against opponents.
        opponents: List of (opponent_rating, opponent_rd, score) tuples
        """
        if not opponents:
            # No games played, increase RD due to inactivity
            new_rd = min(math.sqrt(rd * rd + self.c * self.c), self.initial_rd)
            return rating, new_rd
        
        # Calculate variance
        variance_inv = 0.0
        for opp_rating, opp_rd, _ in opponents:
            e = self.expected_score(rating, opp_rating, opp_rd)
            g_rd = self.g(opp_rd)
            variance_inv += g_rd * g_rd * e * (1.0 - e)
        
        variance = 1.0 / variance_inv if variance_inv > 0 else float('inf')
        
        # Calculate improvement
        improvement = 0.0
        for opp_rating, opp_rd, score in opponents:
            e = self.expected_score(rating, opp_rating, opp_rd)
            g_rd = self.g(opp_rd)
            improvement += g_rd * (score - e)
        
        improvement *= variance
        
        # Update rating and RD
        new_rd = 1.0 / math.sqrt(1.0 / (rd * rd) + 1.0 / variance)
        new_rating = rating + new_rd * new_rd * improvement
        
        return new_rating, new_rd


def classify_role(profession: str) -> str:
    """Classify profession into role categories."""
    dps_roles = {
        'Catalyst', 'Weaver', 'Tempest', 'Berserker', 'Spellbreaker', 'Warrior',
        'Reaper', 'Scourge', 'Harbinger', 'Necromancer', 'Holosmith', 'Scrapper', 
        'Mechanist', 'Engineer', 'Dragonhunter', 'Willbender', 'Guardian',
        'Soulbeast', 'Untamed', 'Ranger', 'Specter', 'Daredevil', 'Thief',
        'Vindicator', 'Herald', 'Renegade', 'Virtuoso', 'Mirage', 'Mesmer',
        'Bladesworn'
    }
    
    support_roles = {
        'Druid', 'Firebrand', 'Chronomancer'
    }
    
    if profession in dps_roles:
        return 'DPS'
    elif profession in support_roles:
        return 'Support'
    else:
        return 'Hybrid'


def determine_win_condition(player_data: Dict, session_data: List[Dict], role: str) -> float:
    """
    Determine if a player "won" based on their role and performance.
    Returns: 1.0 for win, 0.5 for average, 0.0 for poor performance
    
    This is a placeholder - you'll need to define what constitutes a "win"
    """
    # Example logic - you can modify this based on your criteria
    
    if role == 'DPS':
        # For DPS, compare against other DPS players in the same session
        dps_players = [p for p in session_data if classify_role(p['profession']) == 'DPS']
        if len(dps_players) <= 1:
            return 0.5  # Can't compare, neutral score
        
        # Sort by DPS and see where this player ranks
        dps_players.sort(key=lambda x: x['target_dps'], reverse=True)
        player_rank = next((i for i, p in enumerate(dps_players) 
                           if p['account_name'] == player_data['account_name']), len(dps_players))
        
        # Top 25% = win, bottom 25% = loss, middle = draw
        if player_rank < len(dps_players) * 0.25:
            return 1.0
        elif player_rank > len(dps_players) * 0.75:
            return 0.0
        else:
            return 0.5
    
    elif role == 'Support':
        # For support, could look at healing, boon uptime, etc.
        # For now, just give neutral scores since we don't have support stats parsed yet
        return 0.5
    
    else:  # Hybrid
        return 0.5


def calculate_ratings_for_session(db_path: str, timestamp: str, rating_system: str = 'elo'):
    """Calculate rating changes for all players in a session."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all players from this session
    cursor.execute('''
        SELECT account_name, profession, target_dps, all_damage, fight_time, party
        FROM player_performances 
        WHERE timestamp = ?
    ''', (timestamp,))
    
    session_players = cursor.fetchall()
    if len(session_players) < 2:
        conn.close()
        return  # Need at least 2 players
    
    # Convert to dict format
    session_data = []
    for row in session_players:
        session_data.append({
            'account_name': row[0],
            'profession': row[1], 
            'target_dps': row[2],
            'all_damage': row[3],
            'fight_time': row[4],
            'party': row[5]
        })
    
    # Process ratings
    elo_system = EloRatingSystem()
    glicko_system = GlickoRatingSystem()
    
    rating_updates = []
    
    for player in session_data:
        role = classify_role(player['profession'])
        
        # Get current rating
        cursor.execute('''
            SELECT elo_rating, glicko_rating, glicko_rd, games_played, wins, losses
            FROM player_ratings 
            WHERE account_name = ? AND profession = ? AND role = ?
        ''', (player['account_name'], player['profession'], role))
        
        rating_row = cursor.fetchone()
        if rating_row:
            current_elo, current_glicko, current_rd, games, wins, losses = rating_row
        else:
            current_elo, current_glicko, current_rd, games, wins, losses = 1200.0, 1500.0, 200.0, 0, 0, 0
        
        # Determine performance score
        performance_score = determine_win_condition(player, session_data, role)
        
        # Update games played and wins/losses
        games += 1
        if performance_score > 0.5:
            wins += 1
        elif performance_score < 0.5:
            losses += 1
        
        rating_updates.append({
            'account_name': player['account_name'],
            'profession': player['profession'],
            'role': role,
            'old_elo': current_elo,
            'old_glicko': current_glicko,
            'old_rd': current_rd,
            'performance_score': performance_score,
            'games_played': games,
            'wins': wins,
            'losses': losses
        })
    
    # For now, just update individual ratings based on performance
    # In a more sophisticated system, you'd match players against each other
    for update in rating_updates:
        # Simple ELO update against "average" opponent
        avg_elo = 1200.0  # Could calculate session average
        new_elo, _ = elo_system.update_ratings(update['old_elo'], avg_elo, update['performance_score'])
        
        # Update database
        cursor.execute('''
            INSERT OR REPLACE INTO player_ratings 
            (account_name, profession, role, elo_rating, glicko_rating, glicko_rd, games_played, wins, losses)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            update['account_name'], update['profession'], update['role'],
            new_elo, update['old_glicko'], update['old_rd'],
            update['games_played'], update['wins'], update['losses']
        ))
    
    conn.commit()
    conn.close()


def recalculate_all_ratings(db_path: str):
    """Recalculate ratings for all sessions chronologically."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing ratings
    cursor.execute('DELETE FROM player_ratings')
    
    # Get all timestamps in chronological order
    cursor.execute('SELECT DISTINCT timestamp FROM player_performances ORDER BY timestamp')
    timestamps = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    print(f"Recalculating ratings for {len(timestamps)} sessions...")
    for i, timestamp in enumerate(timestamps):
        print(f"Processing session {i+1}/{len(timestamps)}: {timestamp}")
        calculate_ratings_for_session(db_path, timestamp)


def show_leaderboard(db_path: str, role: str = None, limit: int = 20):
    """Show current leaderboard rankings."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if role:
        query = '''
            SELECT account_name, profession, role, elo_rating, games_played, wins, losses
            FROM player_ratings 
            WHERE role = ?
            ORDER BY elo_rating DESC
            LIMIT ?
        '''
        cursor.execute(query, (role, limit))
    else:
        query = '''
            SELECT account_name, profession, role, elo_rating, games_played, wins, losses
            FROM player_ratings 
            ORDER BY elo_rating DESC
            LIMIT ?
        '''
        cursor.execute(query, (limit,))
    
    results = cursor.fetchall()
    conn.close()
    
    print(f"\n=== {'Leaderboard' if not role else f'{role} Leaderboard'} ===")
    print(f"{'Rank':<4} {'Account':<25} {'Profession':<15} {'Role':<8} {'ELO':<6} {'Games':<6} {'W/L':<8}")
    print("-" * 85)
    
    for i, row in enumerate(results, 1):
        account, prof, role_name, elo, games, wins, losses = row
        win_rate = f"{wins}/{losses}" if games > 0 else "0/0"
        print(f"{i:<4} {account:<25} {prof:<15} {role_name:<8} {elo:<6.0f} {games:<6} {win_rate:<8}")


def main():
    parser = argparse.ArgumentParser(description='GW2 Rating System')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('--recalculate', action='store_true', help='Recalculate all ratings')
    parser.add_argument('--leaderboard', action='store_true', help='Show leaderboard')
    parser.add_argument('--role', choices=['DPS', 'Support', 'Hybrid'], help='Filter by role')
    parser.add_argument('--limit', type=int, default=20, help='Number of entries to show')
    
    args = parser.parse_args()
    
    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1
    
    if args.recalculate:
        recalculate_all_ratings(args.database)
        print("Rating recalculation complete!")
    
    if args.leaderboard:
        show_leaderboard(args.database, args.role, args.limit)
    
    return 0


if __name__ == '__main__':
    exit(main())