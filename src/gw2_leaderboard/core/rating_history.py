
import sqlite3
from typing import List, Tuple

def create_rating_history_table(db_path: str):
    """Creates the player_rating_history table if it doesn't exist."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_rating_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                profession TEXT NOT NULL,
                metric_category TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                rating REAL NOT NULL,
                rating_deviation REAL NOT NULL,
                volatility REAL NOT NULL,
                UNIQUE(account_name, profession, metric_category, timestamp)
            )
        """)
        conn.commit()

def save_rating_to_history(db_path: str, account_name: str, profession: str, metric_category: str, timestamp: str, rating: float, rd: float, volatility: float):
    """Saves a player's Glicko rating for a specific session to the history table."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO player_rating_history 
            (account_name, profession, metric_category, timestamp, rating, rating_deviation, volatility)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (account_name, profession, metric_category, timestamp, rating, rd, volatility))
        conn.commit()

def calculate_rating_deltas_from_history(db_path: str, metric_category: str = None):
    """Calculates rating deltas from the player_rating_history table."""
    deltas = {}
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Get all players and their last two ratings
        query = """
            SELECT 
                account_name, profession, metric_category, rating, timestamp
            FROM (
                SELECT 
                    account_name, profession, metric_category, rating, timestamp,
                    ROW_NUMBER() OVER (PARTITION BY account_name, profession, metric_category ORDER BY timestamp DESC) as rn
                FROM player_rating_history
                WHERE (? IS NULL OR metric_category = ?)
            ) 
            WHERE rn <= 2
        """
        cursor.execute(query, (metric_category, metric_category))
        rows = cursor.fetchall()

        player_ratings = {}
        for account_name, profession, metric, rating, timestamp in rows:
            key = (account_name, profession, metric)
            if key not in player_ratings:
                player_ratings[key] = []
            player_ratings[key].append(rating)

        for key, ratings in player_ratings.items():
            if len(ratings) == 2:
                deltas[key] = ratings[0] - ratings[1]
            else:
                deltas[key] = 0.0

    return deltas


def get_player_rating_history(db_path: str, account_name: str, profession: str = None, limit_months: int = 6):
    """
    Get rating history for a specific player, optionally filtered by profession.
    
    Args:
        db_path: Path to the SQLite database
        account_name: Player account name
        profession: Optional profession filter (None for all professions)
        limit_months: Limit data to last N months (default 6)
    
    Returns:
        Dict with structure: {
            'metrics': {
                'metric_name': [
                    {'timestamp': 'YYYYMMDDHHMM', 'rating': float, 'profession': str, 'formatted_date': 'YYYY-MM-DD HH:MM'},
                    ...
                ]
            },
            'professions': ['prof1', 'prof2', ...],  # Available professions for this player
            'date_range': {'start': 'YYYYMMDDHHMM', 'end': 'YYYYMMDDHHMM'}
        }
    """
    from datetime import datetime, timedelta
    
    history_data = {
        'metrics': {},
        'professions': [],
        'date_range': {'start': None, 'end': None}
    }
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Calculate date cutoff for limiting history
        cutoff_date = None
        if limit_months:
            cutoff_date = datetime.now() - timedelta(days=limit_months * 30)
            cutoff_timestamp = cutoff_date.strftime('%Y%m%d%H%M')
        
        # Build query with optional profession filter and date limit
        query = """
            SELECT profession, metric_category, timestamp, rating, rating_deviation, volatility
            FROM player_rating_history
            WHERE account_name = ?
        """
        params = [account_name]
        
        if profession:
            query += " AND profession = ?"
            params.append(profession)
            
        if cutoff_date:
            query += " AND timestamp >= ?"
            params.append(cutoff_timestamp)
            
        query += " ORDER BY timestamp ASC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Process results
        professions_set = set()
        timestamps = []
        
        for prof, metric, timestamp, rating, rd, volatility in rows:
            professions_set.add(prof)
            timestamps.append(timestamp)
            
            # Format timestamp for display (YYYYMMDDHHMM -> YYYY-MM-DD HH:MM)
            try:
                dt = datetime.strptime(timestamp, '%Y%m%d%H%M')
                formatted_date = dt.strftime('%Y-%m-%d %H:%M')
            except ValueError:
                formatted_date = timestamp  # Fallback to raw timestamp
            
            # Initialize metric category if not exists
            if metric not in history_data['metrics']:
                history_data['metrics'][metric] = []
            
            # Add data point
            history_data['metrics'][metric].append({
                'timestamp': timestamp,
                'rating': float(rating),
                'profession': prof,
                'formatted_date': formatted_date,
                'rating_deviation': float(rd),
                'volatility': float(volatility)
            })
        
        # Set metadata
        history_data['professions'] = sorted(list(professions_set))
        if timestamps:
            history_data['date_range']['start'] = min(timestamps)
            history_data['date_range']['end'] = max(timestamps)
    
    return history_data


def format_timestamp_for_chart(timestamp: str) -> str:
    """
    Convert YYYYMMDDHHMM timestamp to human-readable format for chart display.
    
    Args:
        timestamp: Timestamp in YYYYMMDDHHMM format
        
    Returns:
        Formatted string like "2025-07-04 18:30" or original if parsing fails
    """
    try:
        dt = datetime.strptime(timestamp, '%Y%m%d%H%M')
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, ImportError):
        return timestamp


if __name__ == '__main__':
    # Example usage:
    # python -m gw2_leaderboard.core.rating_history
    import os
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'gw2_comprehensive.db')
    create_rating_history_table(db_path)
    print(f"Table 'player_rating_history' created or already exists in {db_path}")
