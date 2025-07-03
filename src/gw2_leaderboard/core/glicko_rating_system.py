#!/usr/bin/env python3
"""
Glicko-based rating system for GW2 WvW leaderboard.
Uses session-relative z-scores to handle varying combat contexts (GvG vs keep takes).
"""

import sqlite3
import math
import argparse
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, date, timedelta


@dataclass
class GlickoRating:
    account_name: str
    profession: str
    metric_category: str
    rating: float = 1500.0  # Glicko default
    rd: float = 350.0      # Rating Deviation (uncertainty)
    volatility: float = 0.06  # Expected fluctuation
    games_played: int = 0


class GlickoSystem:
    """Glicko rating system implementation optimized for WvW performance metrics."""
    
    def __init__(self):
        # Glicko-2 constants
        self.tau = 0.5  # System constant (volatility change)
        self.epsilon = 0.000001  # Convergence tolerance
        
    def mu(self, rating: float) -> float:
        """Convert rating to Glicko-2 scale."""
        return (rating - 1500) / 173.7178
    
    def phi(self, rd: float) -> float:
        """Convert RD to Glicko-2 scale."""
        return rd / 173.7178
    
    def rating_from_mu(self, mu: float) -> float:
        """Convert mu back to rating scale."""
        return mu * 173.7178 + 1500
    
    def rd_from_phi(self, phi: float) -> float:
        """Convert phi back to RD scale."""
        return phi * 173.7178
    
    def g(self, phi: float) -> float:
        """Glicko-2 g function."""
        return 1 / math.sqrt(1 + 3 * phi * phi / (math.pi * math.pi))
    
    def E(self, mu: float, mu_j: float, phi_j: float) -> float:
        """Expected outcome function."""
        return 1 / (1 + math.exp(-self.g(phi_j) * (mu - mu_j)))
    
    def z_score_to_outcome(self, z_score: float) -> float:
        """
        Convert z-score to outcome value for Glicko.
        Uses sigmoid curve to better distinguish performance levels:
        z > 2.0: Outstanding performance (~0.95)
        z = 1.0: Good performance (~0.75)
        z = 0.0: Average performance (0.5) 
        z = -1.0: Poor performance (~0.25)
        z < -2.0: Very poor performance (~0.05)
        """
        # Use sigmoid function for more granular distinction
        # Sigmoid: 1 / (1 + exp(-x))
        # Scale and shift: we want z=0 to give 0.5
        return 1.0 / (1.0 + math.exp(-z_score * 1.5))
    
    def update_rating(self, rating: float, rd: float, volatility: float, 
                     z_scores: List[float]) -> Tuple[float, float, float]:
        """
        Update Glicko rating based on z-scores from multiple sessions.
        For simplicity, we'll treat session average as opponent with rating 1500, RD 150.
        """
        if not z_scores:
            # No games, just increase RD due to inactivity
            new_rd = min(math.sqrt(rd * rd + volatility * volatility), 350)
            return rating, new_rd, volatility
        
        # Convert to Glicko-2 scale
        mu = self.mu(rating)
        phi = self.phi(rd)
        
        # For each z-score, calculate against "average player"
        outcomes = [self.z_score_to_outcome(z) for z in z_scores]
        
        # Use session average as opponent (rating=1500, rd=150)
        opponent_mu = self.mu(1500)
        opponent_phi = self.phi(150)
        
        # Calculate variance
        v_inv = 0
        for _ in outcomes:
            g_val = self.g(opponent_phi)
            E_val = self.E(mu, opponent_mu, opponent_phi)
            v_inv += g_val * g_val * E_val * (1 - E_val)
        
        v = 1 / v_inv if v_inv > 0 else float('inf')
        
        # Calculate improvement
        delta = 0
        for outcome in outcomes:
            g_val = self.g(opponent_phi)
            E_val = self.E(mu, opponent_mu, opponent_phi)
            delta += g_val * (outcome - E_val)
        delta *= v
        
        # Update volatility (simplified)
        new_volatility = volatility  # Could implement full volatility update
        
        # Update rating and RD
        phi_star = math.sqrt(phi * phi + new_volatility * new_volatility)
        new_phi = 1 / math.sqrt(1 / (phi_star * phi_star) + 1 / v)
        new_mu = mu + new_phi * new_phi * (delta / v)
        
        # Convert back to original scale
        new_rating = self.rating_from_mu(new_mu)
        new_rd = self.rd_from_phi(new_phi)
        
        return new_rating, new_rd, new_volatility


# Define metric categories and their database column names
METRIC_CATEGORIES = {
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
    'Burst Consistency': 'burst_consistency_1s'
}

# Profession-specific metric weightings for composite scores
PROFESSION_METRICS = {
    'Firebrand': {
        'metrics': ['Stability', 'Resistance'],
        'weights': [0.6, 0.4]  # Stability more important
    },
    'Chronomancer': {
        'metrics': ['Stability', 'Cleanses', 'Resistance', 'Healing', 'Barrier'],
        'weights': [0.35, 0.35, 0.15, 0.1, 0.05]  # Stability/Cleanses most important
    },
    'Scourge': {
        'metrics': ['Strips', 'DPS'],
        'weights': [0.7, 0.3]  # Strips more important
    },
    'Druid': {
        'metrics': ['Healing', 'Cleanses'],
        'weights': [0.6, 0.4]  # Healing more important
    },
    'China DH': {
        'metrics': ['Stability', 'DPS'],
        'weights': [0.7, 0.3]  # Stability much more important for China DH
    },
    'Condi Firebrand': {
        'metrics': ['Stability', 'Cleanses', 'DPS'],
        'weights': [0.5, 0.3, 0.2]  # Stability most important, then cleanses
    },
    'Support Spb': {
        'metrics': ['Might', 'Resistance', 'Stability', 'Cleanses'],
        'weights': [0.4, 0.3, 0.2, 0.1]  # Might most important
    },
    'Boon Vindi': {
        'metrics': ['Protection', 'DPS'],
        'weights': [0.7, 0.3]  # Protection much more important for Boon Vindi
    }
}


def parse_date_filter(date_filter: str, verbose: bool = True) -> Optional[date]:
    """
    Parse date filter strings like '90d', '6m', '1w', etc.
    Returns the cutoff date (sessions on or after this date will be included).
    """
    if not date_filter:
        return None
    
    today = date.today()
    
    # Parse format like "90d", "6m", "1w"
    if date_filter.endswith('d'):
        days = int(date_filter[:-1])
        return today - timedelta(days=days)
    elif date_filter.endswith('w'):
        weeks = int(date_filter[:-1])
        return today - timedelta(weeks=weeks)
    elif date_filter.endswith('m'):
        months = int(date_filter[:-1])
        # Approximate months as 30 days each
        return today - timedelta(days=months * 30)
    elif date_filter.endswith('y'):
        years = int(date_filter[:-1])
        return today - timedelta(days=years * 365)
    else:
        # Try to parse as YYYY-MM-DD
        try:
            return datetime.strptime(date_filter, '%Y-%m-%d').date()
        except ValueError:
            if verbose:
                print(f"Invalid date filter format: {date_filter}")
                print("Use formats like: 90d (90 days), 6m (6 months), 1w (1 week), 1y (1 year), or YYYY-MM-DD")
            return None


def build_date_filter_clause(date_filter: str = None) -> Tuple[str, List]:
    """
    Build SQL WHERE clause for date filtering.
    Returns (where_clause, parameters) tuple.
    """
    if not date_filter:
        return "", []
    
    cutoff_date = parse_date_filter(date_filter)
    if not cutoff_date:
        return "", []
    
    return "AND parsed_date >= ?", [cutoff_date.isoformat()]


def calculate_session_stats(db_path: str, timestamp: str, metric_category: str, guild_filter: bool = False) -> Tuple[float, float, List[Dict]]:
    """Calculate session mean, std dev, and player data with rankings for a metric."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    metric_column = METRIC_CATEGORIES[metric_category]
    
    # First, get all non-zero values to calculate dynamic floor for support metrics
    if guild_filter:
        initial_query = f'''
            SELECT p.{metric_column}
            FROM player_performances p
            INNER JOIN guild_members g ON p.account_name = g.account_name
            WHERE p.timestamp = ? AND p.{metric_column} > 0
            ORDER BY p.{metric_column} DESC
        '''
    else:
        initial_query = f'''
            SELECT {metric_column}
            FROM player_performances 
            WHERE timestamp = ? AND {metric_column} > 0
            ORDER BY {metric_column} DESC
        '''
    
    cursor.execute(initial_query, (timestamp,))
    all_values = [row[0] for row in cursor.fetchall()]
    
    # Calculate dynamic floor for support metrics (non-DPS)
    dynamic_floor = 0
    support_metrics = ['Healing', 'Barrier', 'Cleanses', 'Strips', 'Stability', 'Resistance', 'Might', 'Protection']
    
    if metric_category in support_metrics and len(all_values) >= 4:
        # Use 25th percentile as dynamic floor to exclude low outliers
        # This ensures we only include players who are meaningfully contributing to this metric
        all_values_sorted = sorted(all_values)
        percentile_25_index = max(0, int(len(all_values_sorted) * 0.25) - 1)
        dynamic_floor = all_values_sorted[percentile_25_index]
        
        # Fallback: if 25th percentile is still very low, use median for stricter filtering
        if dynamic_floor < (statistics.mean(all_values_sorted) * 0.1):  # Less than 10% of mean
            median_index = len(all_values_sorted) // 2
            dynamic_floor = all_values_sorted[median_index]
    
    # Now get filtered results using the dynamic floor
    if guild_filter:
        query = f'''
            SELECT p.account_name, p.profession, p.{metric_column}
            FROM player_performances p
            INNER JOIN guild_members g ON p.account_name = g.account_name
            WHERE p.timestamp = ? AND p.{metric_column} > ?
            ORDER BY p.{metric_column} DESC
        '''
    else:
        query = f'''
            SELECT account_name, profession, {metric_column}
            FROM player_performances 
            WHERE timestamp = ? AND {metric_column} > ?
            ORDER BY {metric_column} DESC
        '''
    
    cursor.execute(query, (timestamp, dynamic_floor))
    results = cursor.fetchall()
    conn.close()
    
    # Ensure we have minimum participants for meaningful z-scores
    if len(results) < 2:
        # If dynamic floor filtered too aggressively, fall back to simple > 0 filter
        if dynamic_floor > 0:
            return calculate_session_stats_fallback(db_path, timestamp, metric_category, guild_filter)
        return 0.0, 1.0, []  # Not enough data
    
    values = [row[2] for row in results]
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 1.0
    
    # Avoid division by zero
    if std_val == 0:
        std_val = 1.0
    
    total_players = len(results)
    players = []
    
    for rank, (account_name, profession, metric_value) in enumerate(results, 1):
        z_score = (metric_value - mean_val) / std_val
        # Calculate normalized rank as percentile (0-100)
        normalized_rank = (rank / total_players) * 100
        
        players.append({
            'account_name': account_name,
            'profession': profession,
            'metric_value': metric_value,
            'z_score': z_score,
            'rank': rank,
            'total_players': total_players,
            'normalized_rank': normalized_rank
        })
    
    return mean_val, std_val, players


def calculate_session_stats_fallback(db_path: str, timestamp: str, metric_category: str, guild_filter: bool = False) -> Tuple[float, float, List[Dict]]:
    """Fallback function using simple > 0 filter when dynamic floor is too aggressive."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    metric_column = METRIC_CATEGORIES[metric_category]
    
    if guild_filter:
        query = f'''
            SELECT p.account_name, p.profession, p.{metric_column}
            FROM player_performances p
            INNER JOIN guild_members g ON p.account_name = g.account_name
            WHERE p.timestamp = ? AND p.{metric_column} > 0
            ORDER BY p.{metric_column} DESC
        '''
    else:
        query = f'''
            SELECT account_name, profession, {metric_column}
            FROM player_performances 
            WHERE timestamp = ? AND {metric_column} > 0
            ORDER BY {metric_column} DESC
        '''
    
    cursor.execute(query, (timestamp,))
    results = cursor.fetchall()
    conn.close()
    
    if len(results) < 2:
        return 0.0, 1.0, []  # Not enough data
    
    values = [row[2] for row in results]
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 1.0
    
    if std_val == 0:
        std_val = 1.0
    
    total_players = len(results)
    players = []
    
    for rank, (account_name, profession, metric_value) in enumerate(results, 1):
        z_score = (metric_value - mean_val) / std_val
        normalized_rank = (rank / total_players) * 100
        
        players.append({
            'account_name': account_name,
            'profession': profession,
            'metric_value': metric_value,
            'z_score': z_score,
            'rank': rank,
            'total_players': total_players,
            'normalized_rank': normalized_rank
        })
    
    return mean_val, std_val, players


def get_current_glicko_rating(db_path: str, account_name: str, profession: str, metric_category: str) -> Tuple[float, float, float, int, float, float]:
    """Get current Glicko rating and stats."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT rating, rd, volatility, games_played, total_rank_sum, total_stat_value
        FROM glicko_ratings 
        WHERE account_name = ? AND profession = ? AND metric_category = ?
    ''', (account_name, profession, metric_category))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0], result[1], result[2], result[3], result[4], result[5]
    else:
        return 1500.0, 350.0, 0.06, 0, 0.0, 0.0  # Default Glicko values


def calculate_profession_session_performance(db_path: str, timestamp: str, profession: str, guild_filter: bool = False) -> List[Dict]:
    """
    Calculate profession-specific performance for a session using weighted z-scores.
    Returns list of player performance data with profession-specific composite z-scores.
    """
    if profession not in PROFESSION_METRICS:
        return []
    
    prof_config = PROFESSION_METRICS[profession]
    metrics = prof_config['metrics']
    weights = prof_config['weights']
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all players of this profession in this session
    if guild_filter:
        query = '''
            SELECT DISTINCT p.account_name
            FROM player_performances p
            INNER JOIN guild_members g ON p.account_name = g.account_name
            WHERE p.timestamp = ? AND p.profession = ?
        '''
    else:
        query = '''
            SELECT DISTINCT account_name
            FROM player_performances 
            WHERE timestamp = ? AND profession = ?
        '''
    
    cursor.execute(query, (timestamp, profession))
    players = [row[0] for row in cursor.fetchall()]
    
    if len(players) < 2:  # Need at least 2 players for z-score calculation
        conn.close()
        return []
    
    player_performances = []
    
    # Calculate session performance for each metric
    metric_session_data = {}
    for metric in metrics:
        mean_val, std_val, session_players = calculate_session_stats(db_path, timestamp, metric, guild_filter)
        if session_players:
            # Filter to only players of this profession
            prof_players = [p for p in session_players if p['account_name'] in players]
            if len(prof_players) >= 2:
                metric_session_data[metric] = prof_players
    
    # Combine weighted z-scores for each player
    for account_name in players:
        weighted_z_score = 0.0
        total_weight = 0.0
        player_data = {'account_name': account_name, 'profession': profession}
        
        for metric, weight in zip(metrics, weights):
            if metric in metric_session_data:
                # Find this player's performance in this metric
                for player_perf in metric_session_data[metric]:
                    if player_perf['account_name'] == account_name:
                        weighted_z_score += player_perf['z_score'] * weight
                        total_weight += weight
                        
                        # Store individual metric data for display
                        player_data[f'{metric.lower()}_value'] = player_perf['metric_value']
                        player_data[f'{metric.lower()}_rank'] = player_perf['normalized_rank']
                        break
        
        if total_weight > 0:
            player_data['weighted_z_score'] = weighted_z_score / total_weight
            player_data['total_players'] = len(players)
            player_performances.append(player_data)
    
    conn.close()
    return player_performances


def recalculate_profession_ratings(db_path: str, profession: str, date_filter: str = None, guild_filter: bool = False, progress_callback=None):
    """
    Calculate profession-specific Glicko ratings using session-based weighted z-scores.
    """
    if profession not in PROFESSION_METRICS:
        return
    
    # Handle date filtering for session selection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    date_clause, date_params = build_date_filter_clause(date_filter)
    if guild_filter:
        query = f"SELECT DISTINCT p.timestamp FROM player_performances p INNER JOIN guild_members g ON p.account_name = g.account_name WHERE p.profession = ? {date_clause} ORDER BY p.timestamp"
    else:
        query = f"SELECT DISTINCT timestamp FROM player_performances WHERE profession = ? {date_clause} ORDER BY timestamp"
    params = [profession] + date_params
    
    cursor.execute(query, params)
    timestamps = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not timestamps:
        return {}
    
    # Create temporary profession ratings table
    import tempfile
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db_path = temp_db.name
    temp_db.close()
    
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE profession_ratings (
            account_name TEXT PRIMARY KEY,
            profession TEXT NOT NULL,
            rating REAL DEFAULT 1500.0,
            rd REAL DEFAULT 350.0,
            volatility REAL DEFAULT 0.06,
            games_played INTEGER DEFAULT 0,
            total_rank_sum REAL DEFAULT 0.0,
            average_rank REAL DEFAULT 0.0,
            weighted_avg_stats TEXT DEFAULT '',
            composite_score REAL DEFAULT 1500.0
        )
    ''')
    
    glicko = GlickoSystem()
    
    total_sessions = len(timestamps)
    # Process each session chronologically
    for i, timestamp in enumerate(timestamps):
        if progress_callback:
            progress_callback(i + 1, total_sessions, timestamp)
        session_performances = calculate_profession_session_performance(db_path, timestamp, profession, guild_filter)
        
        if len(session_performances) < 2:
            continue
        
        # Calculate ranks within this session
        session_performances.sort(key=lambda x: x['weighted_z_score'], reverse=True)
        total_players = len(session_performances)
        
        for rank, player_perf in enumerate(session_performances, 1):
            account_name = player_perf['account_name']
            z_score = player_perf['weighted_z_score']
            normalized_rank = (rank / total_players) * 100
            
            # Get current rating
            cursor.execute('SELECT rating, rd, volatility, games_played, total_rank_sum FROM profession_ratings WHERE account_name = ?', (account_name,))
            result = cursor.fetchone()
            
            if result:
                rating, rd, volatility, games, total_rank_sum = result
            else:
                rating, rd, volatility, games, total_rank_sum = 1500.0, 350.0, 0.06, 0, 0.0
            
            # Update rating
            new_rating, new_rd, new_volatility = glicko.update_rating(rating, rd, volatility, [z_score])
            new_games = games + 1
            new_total_rank_sum = total_rank_sum + rank
            new_average_rank = new_total_rank_sum / new_games
            
            # Calculate composite score with participation bonus
            composite_score = calculate_composite_score(new_rating, new_average_rank, new_rd)
            
            # Store weighted average stats for display
            prof_config = PROFESSION_METRICS[profession]
            stat_parts = []
            for metric in prof_config['metrics'][:3]:  # First 3 metrics for display
                metric_key = f'{metric.lower()}_value'
                if metric_key in player_perf:
                    stat_parts.append(f"{metric[:4]}:{player_perf[metric_key]:.1f}")
            weighted_avg_stats = " ".join(stat_parts)
            
            cursor.execute('''
                INSERT OR REPLACE INTO profession_ratings 
                (account_name, profession, rating, rd, volatility, games_played, total_rank_sum, average_rank, weighted_avg_stats, composite_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (account_name, profession, new_rating, new_rd, new_volatility, new_games, new_total_rank_sum, new_average_rank, weighted_avg_stats, composite_score))
    
    conn.commit()
    
    # Get final results
    cursor.execute('''
        SELECT account_name, rating, games_played, average_rank, composite_score, weighted_avg_stats
        FROM profession_ratings 
        ORDER BY composite_score DESC
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    # Cleanup temporary database
    import os
    try:
        os.unlink(temp_db_path)
    except OSError:
        pass
    
    return results


def calculate_composite_score(glicko_rating: float, average_rank_percentile: float, rd: float = 350.0) -> float:
    """
    Calculate composite score combining Glicko rating (50%) and rank performance (50%) with participation bonus.
    
    Args:
        glicko_rating: Base Glicko rating (around 1500 +/- 500)
        average_rank_percentile: Average rank as percentile (0-100, lower is better)
        rd: Rating Deviation (lower = more confident/experienced player)
    
    Returns:
        Composite score where rank performance heavily influences final ranking, 
        with bonus for frequent participation (lower RD)
    """
    if average_rank_percentile <= 0:
        return glicko_rating  # No rank data yet
    
    # Convert rank percentile to bonus/penalty (increased impact)
    # 0-5% rank = +250 to +200 bonus (elite performers)
    # 5-15% rank = +200 to +100 bonus (very good)
    # 15-35% rank = +100 to +25 bonus (above average)
    # 35-65% rank = +25 to -25 penalty (average)
    # 65-85% rank = -25 to -100 penalty (below average)
    # 85-100% rank = -100 to -250 penalty (poor performers)
    
    if average_rank_percentile <= 5:
        # Elite tier: 0-5% rank gets +200 to +250 bonus
        rank_bonus = 250 - (average_rank_percentile * 10)  # 250 at 0%, 200 at 5%
    elif average_rank_percentile <= 15:
        # Very good: 5-15% rank gets +100 to +200 bonus
        rank_bonus = 200 - ((average_rank_percentile - 5) * 10)
    elif average_rank_percentile <= 35:
        # Above average: 15-35% rank gets +25 to +100 bonus
        rank_bonus = 100 - ((average_rank_percentile - 15) * 3.75)
    elif average_rank_percentile <= 65:
        # Average: 35-65% rank gets -25 to +25
        rank_bonus = 25 - ((average_rank_percentile - 35) * 1.67)
    elif average_rank_percentile <= 85:
        # Below average: 65-85% rank gets -25 to -100 penalty
        rank_bonus = -25 - ((average_rank_percentile - 65) * 3.75)
    else:
        # Poor: 85-100% rank gets -100 to -250 penalty
        rank_bonus = -100 - ((average_rank_percentile - 85) * 10)
    
    # Calculate participation confidence multiplier based on Rating Deviation
    # Lower RD (more games) = higher confidence = rating boost
    # RD starts at 350 (new player), decreases with more games
    # Formula gives 0-2% bonus for experienced players
    confidence_multiplier = 1.0 + max(0, (350 - rd) / 350 * 0.02)
    
    # Combine: 50% Glicko + 50% rank performance (much higher rank impact)
    base_composite = (glicko_rating * 0.5) + ((glicko_rating + rank_bonus) * 0.5)
    
    # Apply participation confidence multiplier
    composite = base_composite * confidence_multiplier
    
    return composite


def update_glicko_rating(db_path: str, account_name: str, profession: str, metric_category: str,
                        rating: float, rd: float, volatility: float, games_played: int, 
                        total_rank_sum: float, average_rank: float, total_stat_value: float, average_stat_value: float):
    """Update Glicko rating and composite score in database."""
    # Calculate composite score with participation bonus
    composite_score = calculate_composite_score(rating, average_rank, rd)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO glicko_ratings 
        (account_name, profession, metric_category, rating, rd, volatility, games_played, total_rank_sum, average_rank, total_stat_value, average_stat_value, composite_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (account_name, profession, metric_category, rating, rd, volatility, games_played, total_rank_sum, average_rank, total_stat_value, average_stat_value, composite_score))
    
    conn.commit()
    conn.close()


def create_glicko_database(db_path: str):
    """Create Glicko ratings table."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('DROP TABLE IF EXISTS glicko_ratings')
    cursor.execute('''
        CREATE TABLE glicko_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            profession TEXT NOT NULL,
            metric_category TEXT NOT NULL,
            rating REAL DEFAULT 1500.0,
            rd REAL DEFAULT 350.0,
            volatility REAL DEFAULT 0.06,
            games_played INTEGER DEFAULT 0,
            total_rank_sum REAL DEFAULT 0.0,
            average_rank REAL DEFAULT 0.0,
            total_stat_value REAL DEFAULT 0.0,
            average_stat_value REAL DEFAULT 0.0,
            composite_score REAL DEFAULT 1500.0,
            UNIQUE(account_name, profession, metric_category)
        )
    ''')
    
    conn.commit()
    conn.close()


def _process_metric_for_session(db_path: str, timestamp: str, metric_category: str, guild_filter: bool = False):
    """Process a single metric category for a session."""
    import threading
    glicko = GlickoSystem()
    thread_name = threading.current_thread().name
    
    # Get session statistics and z-scores
    mean_val, std_val, players = calculate_session_stats(db_path, timestamp, metric_category, guild_filter)
    
    if len(players) < 2:
        return f"[{thread_name}] {metric_category}: skipped (insufficient players)"
    
    # Update each player's rating
    for player in players:
        account_name = player['account_name']
        profession = player['profession']
        z_score = player['z_score']
        normalized_rank = player['normalized_rank']
        rank = player['rank']
        metric_value = player['metric_value']
        
        # Get current rating and stat tracking
        rating, rd, volatility, games, total_rank_sum, total_stat_value = get_current_glicko_rating(
            db_path, account_name, profession, metric_category)
        
        # Update rating based on this z-score
        new_rating, new_rd, new_volatility = glicko.update_rating(
            rating, rd, volatility, [z_score])
        
        # Update rank tracking
        new_total_rank_sum = total_rank_sum + rank
        new_games = games + 1
        new_average_rank = new_total_rank_sum / new_games
        
        # Update stat tracking
        new_total_stat_value = total_stat_value + metric_value
        new_average_stat_value = new_total_stat_value / new_games
        
        # Store updated rating, rank, and stat data
        update_glicko_rating(db_path, account_name, profession, metric_category,
                           new_rating, new_rd, new_volatility, new_games, 
                           new_total_rank_sum, new_average_rank, new_total_stat_value, new_average_stat_value)
    
    return f"[{thread_name}] {metric_category}: processed {len(players)} players"


def calculate_glicko_ratings_for_session(db_path: str, timestamp: str, guild_filter: bool = False):
    """Calculate Glicko rating changes for all players in a session."""
    # Due to SQLite write locking, process metrics sequentially but optimize individual operations
    glicko = GlickoSystem()
    
    for metric_category in METRIC_CATEGORIES.keys():
        # Get session statistics and z-scores
        mean_val, std_val, players = calculate_session_stats(db_path, timestamp, metric_category, guild_filter)
        
        if len(players) < 2:
            continue
        
        # Update each player's rating
        for player in players:
            account_name = player['account_name']
            profession = player['profession']
            z_score = player['z_score']
            normalized_rank = player['normalized_rank']
            rank = player['rank']
            metric_value = player['metric_value']
            
            # Get current rating and stat tracking
            rating, rd, volatility, games, total_rank_sum, total_stat_value = get_current_glicko_rating(
                db_path, account_name, profession, metric_category)
            
            # Update rating based on this z-score
            new_rating, new_rd, new_volatility = glicko.update_rating(
                rating, rd, volatility, [z_score])
            
            # Update rank tracking
            new_total_rank_sum = total_rank_sum + rank
            new_games = games + 1
            new_average_rank = new_total_rank_sum / new_games
            
            # Update stat tracking
            new_total_stat_value = total_stat_value + metric_value
            new_average_stat_value = new_total_stat_value / new_games
            
            # Store updated rating, rank, and stat data
            update_glicko_rating(db_path, account_name, profession, metric_category,
                               new_rating, new_rd, new_volatility, new_games, 
                               new_total_rank_sum, new_average_rank, new_total_stat_value, new_average_stat_value)


def recalculate_all_glicko_ratings(db_path: str, guild_filter: bool = False, progress_callback=None):
    """Recalculate all Glicko ratings chronologically."""
    # Create Glicko table
    create_glicko_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all timestamps in chronological order with optional guild filtering
    if guild_filter:
        query = '''
            SELECT DISTINCT p.timestamp 
            FROM player_performances p
            INNER JOIN guild_members g ON p.account_name = g.account_name
            ORDER BY p.timestamp
        '''
    else:
        query = 'SELECT DISTINCT timestamp FROM player_performances ORDER BY timestamp'
    
    cursor.execute(query)
    timestamps = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    total_sessions = len(timestamps)
    for i, timestamp in enumerate(timestamps):
        if progress_callback:
            progress_callback(i + 1, total_sessions, timestamp)
        calculate_glicko_ratings_for_session(db_path, timestamp, guild_filter)


def calculate_date_filtered_ratings(db_path: str, date_filter: str, guild_filter: bool = False, progress_callback=None) -> str:
    """
    Calculate Glicko ratings using only sessions within the date filter.
    Returns path to temporary database with filtered ratings.
    """
    import tempfile
    import shutil
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db_path = temp_db.name
    temp_db.close()
    
    # Copy original database
    shutil.copy2(db_path, temp_db_path)
    
    # Get date filter clause
    date_clause, date_params = build_date_filter_clause(date_filter)
    
    if not date_clause:
        return temp_db_path  # No filtering needed
    
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    
    # Verify guild_members table was copied correctly (for debugging guild recognition issues)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guild_members'")
    guild_table_exists = cursor.fetchone() is not None
    if guild_table_exists:
        cursor.execute("SELECT COUNT(*) FROM guild_members")
        guild_member_count = cursor.fetchone()[0]
        # Only show debug info if there's a progress callback (indicating verbose mode)
        if progress_callback:
            print(f"[DEBUG] Temporary database has guild_members table with {guild_member_count} members")
    
    # Get timestamps within date range
    if guild_filter:
        query = f"SELECT DISTINCT p.timestamp FROM player_performances p INNER JOIN guild_members g ON p.account_name = g.account_name WHERE 1=1 {date_clause} ORDER BY p.timestamp"
    else:
        query = f"SELECT DISTINCT timestamp FROM player_performances WHERE 1=1 {date_clause} ORDER BY timestamp"
    cursor.execute(query, date_params)
    filtered_timestamps = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    if not filtered_timestamps:
        return temp_db_path
    
    total_sessions = len(filtered_timestamps)
    # Recalculate ratings using only filtered sessions
    create_glicko_database(temp_db_path)
    
    glicko = GlickoSystem()
    for i, timestamp in enumerate(filtered_timestamps):
        if progress_callback:
            progress_callback(i + 1, total_sessions, timestamp)
        calculate_glicko_ratings_for_session(temp_db_path, timestamp, guild_filter)
    
    return temp_db_path


def show_glicko_leaderboard(db_path: str, metric_category: str = None, limit: int = 50, date_filter: str = None, include_overall: bool = False):
    """Show Glicko leaderboard for a specific metric category."""
    
    # Handle date filtering
    working_db_path = db_path
    temp_db_cleanup = None
    
    if date_filter:
        working_db_path = calculate_date_filtered_ratings(db_path, date_filter)
        temp_db_cleanup = working_db_path
        if working_db_path == db_path:  # No filtering was applied
            date_filter = None
    
    conn = sqlite3.connect(working_db_path)
    cursor = conn.cursor()
    
    try:
        if metric_category:
            if metric_category not in METRIC_CATEGORIES:
                print(f"Invalid metric category. Choose from: {list(METRIC_CATEGORIES.keys())}")
                return
            
            # Show specific metric category leaderboard
            query = '''
                SELECT account_name, profession, rating, rd, games_played, average_rank, composite_score, average_stat_value
                FROM glicko_ratings 
                WHERE metric_category = ?
                ORDER BY composite_score DESC
                LIMIT ?
            '''
            cursor.execute(query, (metric_category, limit))
            results = cursor.fetchall()
            
            # Determine the unit/format for the stat display
            stat_unit = ""
            if metric_category == "DPS":
                stat_unit = "DPS"
            elif metric_category in ["Healing", "Barrier"]:
                stat_unit = "/sec"
            else:
                stat_unit = "/sec"
            
            date_suffix = f" (Last {date_filter})" if date_filter else ""
            print(f"\n=== {metric_category} Composite Leaderboard{date_suffix} ===")
            print(f"{'Rank':<4} {'Account':<25} {'Profession':<15} {'Comp':<6} {'Glicko':<6} {'Games':<6} {'Avg Rank%':<10} {'Avg ' + metric_category[:4]:<10}")
            print("-" * 120)
            
            for i, row in enumerate(results, 1):
                account, prof, rating, rd, games, avg_rank, composite, avg_stat = row
                avg_rank_display = f"{avg_rank:.1f}%" if avg_rank > 0 else "N/A"
                avg_stat_display = f"{avg_stat:.1f}" if avg_stat > 0 else "N/A"
                print(f"{i:<4} {account:<25} {prof:<15} {composite:<6.0f} {rating:<6.0f} {games:<6} {avg_rank_display:<10} {avg_stat_display:<10}")
            
            # Show overall leaderboard only if specifically requested
            if include_overall:
                query = '''
                    SELECT account_name, profession, metric_category, rating, rd, games_played, composite_score
                    FROM glicko_ratings 
                    ORDER BY composite_score DESC
                    LIMIT ?
                '''
                cursor.execute(query, (limit,))
                overall_results = cursor.fetchall()
                
                date_suffix = f" (Last {date_filter})" if date_filter else ""
                print(f"\n=== Overall Top Composite Performers{date_suffix} ===")
                print(f"{'Rank':<4} {'Account':<25} {'Profession':<15} {'Category':<10} {'Comp':<6} {'Glicko':<6}")
                print("-" * 90)
                
                for i, row in enumerate(overall_results, 1):
                    account, prof, category, rating, rd, games, composite = row
                    print(f"{i:<4} {account:<25} {prof:<15} {category:<10} {composite:<6.0f} {rating:<6.0f}")
        else:
            # Show top players across all categories (when no specific metric is requested)
            query = '''
                SELECT account_name, profession, metric_category, rating, rd, games_played, composite_score
                FROM glicko_ratings 
                ORDER BY composite_score DESC
                LIMIT ?
            '''
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            
            date_suffix = f" (Last {date_filter})" if date_filter else ""
            print(f"\n=== Overall Top Composite Performers{date_suffix} ===")
            print(f"{'Rank':<4} {'Account':<25} {'Profession':<15} {'Category':<10} {'Comp':<6} {'Glicko':<6}")
            print("-" * 90)
            
            for i, row in enumerate(results, 1):
                account, prof, category, rating, rd, games, composite = row
                print(f"{i:<4} {account:<25} {prof:<15} {category:<10} {composite:<6.0f} {rating:<6.0f}")
    
    finally:
        conn.close()
        
        # Cleanup temporary database
        if temp_db_cleanup and temp_db_cleanup != db_path:
            import os
            try:
                os.unlink(temp_db_cleanup)
            except OSError:
                pass


def show_profession_leaderboard(db_path: str, profession: str, limit: int = 50, date_filter: str = None):
    """Show profession-specific leaderboard using session-based weighted composite scores."""
    
    if profession not in PROFESSION_METRICS:
        print(f"No specific metrics defined for profession: {profession}")
        print(f"Available professions: {list(PROFESSION_METRICS.keys())}")
        return
    
    print(f"Calculating {profession} ratings using session-based weighted z-scores...")
    
    # Calculate profession-specific ratings using session-based approach
    results = recalculate_profession_ratings(db_path, profession, date_filter)
    
    if not results:
        print(f"No players found for profession: {profession}")
        return
    
    # Limit results for display
    results = results[:limit]
    
    # Display leaderboard
    prof_config = PROFESSION_METRICS[profession]
    date_suffix = f" (Last {date_filter})" if date_filter else ""
    metrics_str = "/".join(prof_config['metrics'])
    weights_str = "/".join([f"{w:.1f}" for w in prof_config['weights']])
    
    print(f"\n=== {profession} Profession Leaderboard{date_suffix} ===")
    print(f"Session-based weighted metrics: {metrics_str} (Weights: {weights_str})")
    print(f"{'Rank':<4} {'Account':<25} {'Comp':<6} {'Glicko':<6} {'Games':<6} {'Avg Prof Rank%':<14} {'Key Stats'}")
    print("-" * 120)
    
    for i, (account, rating, games, avg_rank, composite, stats_breakdown) in enumerate(results, 1):
        # Show the actual average rank percentage from session-based performance within profession
        avg_rank_display = f"{avg_rank:.1f}%" if avg_rank > 0 else "N/A"
        print(f"{i:<4} {account:<25} {composite:<6.0f} {rating:<6.0f} {games:<6} {avg_rank_display:<14} {stats_breakdown}")
    
    # Show methodology explanation
    print(f"\nNote: Rankings use session-based z-score evaluation within {profession} players only.")
    print(f"Each session compares weighted performance across {len(prof_config['metrics'])} metrics.")


def show_glicko_player_profile(db_path: str, account_name: str):
    """Show comprehensive Glicko profile for a specific player."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT profession, metric_category, rating, rd, volatility, games_played, average_rank, composite_score, average_stat_value
        FROM glicko_ratings 
        WHERE account_name = ?
        ORDER BY composite_score DESC
    ''', (account_name,))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"No rating data found for player: {account_name}")
        return
    
    print(f"\n=== Player Profile: {account_name} ===")
    print(f"{'Profession':<15} {'Category':<10} {'Comp':<6} {'Glicko':<6} {'Avg Rank%':<10} {'Games':<6} {'Avg Stat':<10}")
    print("-" * 95)
    
    for prof, category, rating, rd, volatility, games, avg_rank, composite, avg_stat in results:
        avg_rank_display = f"{avg_rank:.1f}%" if avg_rank > 0 else "N/A"
        avg_stat_display = f"{avg_stat:.1f}" if avg_stat > 0 else "N/A"
        print(f"{prof:<15} {category:<10} {composite:<6.0f} {rating:<6.0f} {avg_rank_display:<10} {games:<6} {avg_stat_display:<10}")
    
    # Show summary
    cursor.execute('''
        SELECT COUNT(DISTINCT profession) as professions,
               COUNT(DISTINCT metric_category) as categories,
               AVG(rating) as avg_rating,
               SUM(games_played) as total_games
        FROM glicko_ratings 
        WHERE account_name = ?
    ''', (account_name,))
    
    summary = cursor.fetchone()
    if summary:
        print(f"\nSummary: {summary[0]} professions, {summary[1]} categories, {summary[2]:.0f} avg rating, {summary[3]} total games")
    
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Glicko-based GW2 Rating System')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('--recalculate', action='store_true', help='Recalculate all Glicko ratings')
    parser.add_argument('--leaderboard', help='Show Glicko leaderboard for specific category')
    parser.add_argument('--all-leaderboards', action='store_true', help='Show leaderboards for all categories')
    parser.add_argument('--player', help='Show Glicko profile for specific player')
    parser.add_argument('--limit', type=int, default=50, help='Number of entries to show')
    parser.add_argument('--date-filter', help='Filter by date (e.g., 90d, 6m, 1w, 1y, or YYYY-MM-DD)')
    parser.add_argument('--include-overall', action='store_true', help='Include overall leaderboard when showing specific category')
    parser.add_argument('--profession', help='Show profession-specific leaderboard (e.g., Firebrand, Chronomancer, Scourge, Druid, "Condi Firebrand", "Support Spb")')
    
    args = parser.parse_args()
    
    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1
    
    if args.recalculate:
        recalculate_all_glicko_ratings(args.database)
        print("Glicko rating recalculation complete!")
    
    if args.leaderboard:
        show_glicko_leaderboard(args.database, args.leaderboard, args.limit, args.date_filter, getattr(args, 'include_overall', False))
    
    if args.all_leaderboards:
        for category in METRIC_CATEGORIES.keys():
            show_glicko_leaderboard(args.database, category, args.limit, args.date_filter, getattr(args, 'include_overall', False))
    
    if args.player:
        show_glicko_player_profile(args.database, args.player)
    
    if args.profession:
        show_profession_leaderboard(args.database, args.profession, args.limit, args.date_filter)
    
    return 0


if __name__ == '__main__':
    exit(main())