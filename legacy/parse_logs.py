#!/usr/bin/env python3
"""
Parse GW2 log summaries to extract player performance data.
"""

import json
import re
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import argparse
from datetime import datetime


@dataclass
class PlayerPerformance:
    timestamp: str
    player_name: str
    account_name: str
    profession: str
    party: int
    fight_time: float
    target_damage: int
    target_dps: int
    target_power: int
    target_power_ps: int
    target_condition: int
    target_condition_ps: int
    all_damage: int
    all_power: int
    all_condition: int
    healing_done: Optional[int] = None
    support_given: Optional[int] = None


def extract_tooltip(text: str) -> str:
    """Extract account name from tooltip attribute."""
    match = re.search(r'data-tooltip="([^"]+)"', text)
    return match.group(1) if match else ""


def parse_damage_table(damage_text: str) -> List[Dict]:
    """Parse the damage table from TiddlyWiki markup."""
    players = []
    
    # Find table rows (lines starting with |)
    lines = damage_text.split('\n')
    data_rows = [line for line in lines if line.startswith('|') and not line.startswith('|!') and not line.startswith('|thead')]
    
    for row in data_rows:
        if '|h' in row or not row.strip():
            continue
            
        # Split by | and clean up
        cells = [cell.strip() for cell in row.split('|') if cell.strip()]
        
        if len(cells) < 14:  # Skip incomplete rows
            continue
            
        try:
            # Extract data based on the table structure we saw
            party = int(cells[0]) if cells[0].isdigit() else 0
            
            # Parse player name and account (from tooltip)
            name_cell = cells[1]
            account_name = extract_tooltip(name_cell)
            # Extract display name (between > and </span>)
            display_match = re.search(r'>([^<]+)</span>', name_cell)
            player_name = display_match.group(1) if display_match else ""
            
            # Parse profession (extract from {{profession}} format)
            prof_cell = cells[2]
            prof_match = re.search(r'{{(\w+)}}', prof_cell)
            profession = prof_match.group(1) if prof_match else ""
            
            # Parse numeric values, removing commas
            fight_time = float(cells[3].replace(',', '')) if cells[3].replace(',', '').replace('.', '').isdigit() else 0
            target_damage = int(cells[4].replace(',', '')) if cells[4].replace(',', '').isdigit() else 0
            target_dps = int(cells[5].replace(',', '')) if cells[5].replace(',', '').isdigit() else 0
            target_power = int(cells[6].replace(',', '')) if cells[6].replace(',', '').isdigit() else 0
            target_power_ps = int(cells[7].replace(',', '')) if cells[7].replace(',', '').isdigit() else 0
            target_condition = int(cells[8].replace(',', '')) if cells[8].replace(',', '').isdigit() else 0
            target_condition_ps = int(cells[9].replace(',', '')) if cells[9].replace(',', '').isdigit() else 0
            all_damage = int(cells[11].replace(',', '')) if cells[11].replace(',', '').isdigit() else 0
            all_power = int(cells[12].replace(',', '')) if cells[12].replace(',', '').isdigit() else 0
            all_condition = int(cells[13].replace(',', '')) if cells[13].replace(',', '').isdigit() else 0
            
            players.append({
                'party': party,
                'player_name': player_name,
                'account_name': account_name,
                'profession': profession,
                'fight_time': fight_time,
                'target_damage': target_damage,
                'target_dps': target_dps,
                'target_power': target_power,
                'target_power_ps': target_power_ps,
                'target_condition': target_condition,
                'target_condition_ps': target_condition_ps,
                'all_damage': all_damage,
                'all_power': all_power,
                'all_condition': all_condition
            })
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing row: {row[:100]}... - {e}")
            continue
    
    return players


def parse_log_directory(log_dir: Path) -> List[PlayerPerformance]:
    """Parse a single log directory and extract player performance data."""
    timestamp = log_dir.name
    
    # Read damage data
    damage_file = log_dir / f"{timestamp}-Damage.json"
    if not damage_file.exists():
        print(f"No damage file found for {timestamp}")
        return []
    
    with open(damage_file, 'r', encoding='utf-8') as f:
        damage_data = json.load(f)
    
    damage_text = damage_data.get('text', '')
    players_data = parse_damage_table(damage_text)
    
    # Convert to PlayerPerformance objects
    performances = []
    for player_data in players_data:
        if not player_data['player_name'] or not player_data['account_name']:
            continue
            
        performance = PlayerPerformance(
            timestamp=timestamp,
            player_name=player_data['player_name'],
            account_name=player_data['account_name'],
            profession=player_data['profession'],
            party=player_data['party'],
            fight_time=player_data['fight_time'],
            target_damage=player_data['target_damage'],
            target_dps=player_data['target_dps'],
            target_power=player_data['target_power'],
            target_power_ps=player_data['target_power_ps'],
            target_condition=player_data['target_condition'],
            target_condition_ps=player_data['target_condition_ps'],
            all_damage=player_data['all_damage'],
            all_power=player_data['all_power'],
            all_condition=player_data['all_condition']
        )
        performances.append(performance)
    
    return performances


def create_database(db_path: str):
    """Create SQLite database with player performance schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_performances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            player_name TEXT NOT NULL,
            account_name TEXT NOT NULL,
            profession TEXT NOT NULL,
            party INTEGER,
            fight_time REAL,
            target_damage INTEGER,
            target_dps INTEGER,
            target_power INTEGER,
            target_power_ps INTEGER,
            target_condition INTEGER,
            target_condition_ps INTEGER,
            all_damage INTEGER,
            all_power INTEGER,
            all_condition INTEGER,
            healing_done INTEGER,
            support_given INTEGER,
            UNIQUE(timestamp, account_name, profession)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            profession TEXT NOT NULL,
            role TEXT NOT NULL,
            elo_rating REAL DEFAULT 1200,
            games_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            UNIQUE(account_name, profession, role)
        )
    ''')
    
    conn.commit()
    conn.close()


def store_performances(performances: List[PlayerPerformance], db_path: str):
    """Store player performances in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for perf in performances:
        cursor.execute('''
            INSERT OR REPLACE INTO player_performances 
            (timestamp, player_name, account_name, profession, party, fight_time,
             target_damage, target_dps, target_power, target_power_ps,
             target_condition, target_condition_ps, all_damage, all_power, all_condition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            perf.timestamp, perf.player_name, perf.account_name, perf.profession,
            perf.party, perf.fight_time, perf.target_damage, perf.target_dps,
            perf.target_power, perf.target_power_ps, perf.target_condition,
            perf.target_condition_ps, perf.all_damage, perf.all_power, perf.all_condition
        ))
    
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Parse GW2 log summaries into database')
    parser.add_argument('logs_dir', help='Directory containing extracted log folders')
    parser.add_argument('-d', '--database', default='gw2_leaderboard.db',
                        help='SQLite database file (default: gw2_leaderboard.db)')
    
    args = parser.parse_args()
    
    logs_path = Path(args.logs_dir)
    if not logs_path.exists():
        print(f"Directory {logs_path} does not exist")
        return 1
    
    # Create database
    create_database(args.database)
    print(f"Created database: {args.database}")
    
    # Process each log directory
    all_performances = []
    for log_dir in sorted(logs_path.iterdir()):
        if log_dir.is_dir() and re.match(r'\d{12}', log_dir.name):
            print(f"Processing {log_dir.name}...")
            performances = parse_log_directory(log_dir)
            all_performances.extend(performances)
            print(f"  Found {len(performances)} player performances")
    
    # Store in database
    if all_performances:
        store_performances(all_performances, args.database)
        print(f"Stored {len(all_performances)} performances in database")
        
        # Show summary
        conn = sqlite3.connect(args.database)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(DISTINCT account_name) FROM player_performances')
        unique_players = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT timestamp) FROM player_performances')
        unique_sessions = cursor.fetchone()[0]
        
        cursor.execute('SELECT profession, COUNT(*) FROM player_performances GROUP BY profession ORDER BY COUNT(*) DESC')
        prof_counts = cursor.fetchall()
        
        print(f"\nSummary:")
        print(f"  Unique players: {unique_players}")
        print(f"  Gaming sessions: {unique_sessions}")
        print(f"  Profession distribution:")
        for prof, count in prof_counts:
            print(f"    {prof}: {count}")
        
        conn.close()
    
    return 0


if __name__ == '__main__':
    exit(main())