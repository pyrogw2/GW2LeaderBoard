
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

if __name__ == '__main__':
    # Example usage:
    # python -m gw2_leaderboard.core.rating_history
    import os
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'gw2_comprehensive.db')
    create_rating_history_table(db_path)
    print(f"Table 'player_rating_history' created or already exists in {db_path}")
