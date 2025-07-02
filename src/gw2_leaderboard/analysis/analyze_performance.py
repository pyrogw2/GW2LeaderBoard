#!/usr/bin/env python3
"""
Analyze GW2 player performance data and generate reports.
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
import json
import csv


def get_player_stats(db_path: str, account_name: str = None):
    """Get player statistics from the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if account_name:
        query = '''
            SELECT * FROM player_performances 
            WHERE account_name = ?
            ORDER BY timestamp DESC
        '''
        cursor.execute(query, (account_name,))
    else:
        cursor.execute('SELECT * FROM player_performances ORDER BY timestamp DESC')
    
    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    
    conn.close()
    return rows, columns


def get_profession_stats(db_path: str):
    """Get profession statistics."""
    conn = sqlite3.connect(db_path)
    
    query = '''
        SELECT 
            profession,
            COUNT(*) as total_performances,
            COUNT(DISTINCT account_name) as unique_players,
            AVG(target_dps) as avg_target_dps,
            MAX(target_dps) as max_target_dps,
            AVG(all_damage) as avg_all_damage,
            MAX(all_damage) as max_all_damage,
            AVG(fight_time) as avg_fight_time
        FROM player_performances 
        WHERE target_dps > 0  -- Filter out invalid entries
        GROUP BY profession
        ORDER BY avg_target_dps DESC
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def get_top_performers(db_path: str, metric: str = 'target_dps', limit: int = 20):
    """Get top performers by a specific metric."""
    conn = sqlite3.connect(db_path)
    
    query = f'''
        SELECT 
            account_name,
            player_name,
            profession,
            timestamp,
            target_dps,
            all_damage,
            fight_time,
            {metric}
        FROM player_performances 
        WHERE {metric} > 0
        ORDER BY {metric} DESC
        LIMIT ?
    '''
    
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    return df


def get_player_progression(db_path: str, account_name: str):
    """Get a player's performance progression over time."""
    conn = sqlite3.connect(db_path)
    
    query = '''
        SELECT 
            timestamp,
            profession,
            target_dps,
            all_damage,
            fight_time,
            target_power,
            target_condition
        FROM player_performances 
        WHERE account_name = ?
        ORDER BY timestamp ASC
    '''
    
    df = pd.read_sql_query(query, conn, params=(account_name,))
    conn.close()
    return df


def analyze_role_performance(db_path: str):
    """Analyze performance by role (DPS, Support, etc.)."""
    conn = sqlite3.connect(db_path)
    
    # Define role classifications based on profession
    dps_professions = ['Catalyst', 'Weaver', 'Tempest', 'Berserker', 'Spellbreaker', 
                      'Reaper', 'Scourge', 'Holosmith', 'Scrapper', 'Dragonhunter', 
                      'Willbender', 'Soulbeast', 'Untamed', 'Specter', 'Vindicator', 
                      'Herald', 'Virtuoso', 'Mirage', 'Harbinger', 'Mechanist', 'Bladesworn']
    
    support_professions = ['Druid', 'Firebrand', 'Chronomancer', 'Renegade']
    
    # Get data for each role
    dps_query = f'''
        SELECT 
            'DPS' as role,
            profession,
            COUNT(*) as performances,
            COUNT(DISTINCT account_name) as unique_players,
            AVG(target_dps) as avg_dps,
            MAX(target_dps) as max_dps,
            AVG(all_damage) as avg_damage
        FROM player_performances 
        WHERE profession IN ({','.join(['?' for _ in dps_professions])})
        AND target_dps > 0
        GROUP BY profession
    '''
    
    support_query = f'''
        SELECT 
            'Support' as role,
            profession,
            COUNT(*) as performances,
            COUNT(DISTINCT account_name) as unique_players,
            AVG(target_dps) as avg_dps,
            MAX(target_dps) as max_dps,
            AVG(all_damage) as avg_damage
        FROM player_performances 
        WHERE profession IN ({','.join(['?' for _ in support_professions])})
        AND target_dps > 0
        GROUP BY profession
    '''
    
    dps_df = pd.read_sql_query(dps_query, conn, params=dps_professions)
    support_df = pd.read_sql_query(support_query, conn, params=support_professions)
    
    conn.close()
    return pd.concat([dps_df, support_df], ignore_index=True)


def export_reports(db_path: str, output_dir: str = 'reports'):
    """Export various analysis reports."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Get profession stats
    prof_stats = get_profession_stats(db_path)
    prof_stats.to_csv(output_path / 'profession_stats.csv', index=False)
    
    # Get top performers
    top_dps = get_top_performers(db_path, 'target_dps', 50)
    top_dps.to_csv(output_path / 'top_dps_performers.csv', index=False)
    
    top_damage = get_top_performers(db_path, 'all_damage', 50)
    top_damage.to_csv(output_path / 'top_damage_performers.csv', index=False)
    
    # Get role analysis
    role_stats = analyze_role_performance(db_path)
    role_stats.to_csv(output_path / 'role_performance.csv', index=False)
    
    # Create summary report
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Overall stats
    cursor.execute('SELECT COUNT(*) FROM player_performances')
    total_performances = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT account_name) FROM player_performances')
    unique_players = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT timestamp) FROM player_performances')
    unique_sessions = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM player_performances')
    date_range = cursor.fetchone()
    
    summary = {
        'total_performances': total_performances,
        'unique_players': unique_players,
        'unique_sessions': unique_sessions,
        'date_range': {
            'start': date_range[0],
            'end': date_range[1]
        },
        'top_dps_overall': {
            'player': top_dps.iloc[0]['account_name'],
            'profession': top_dps.iloc[0]['profession'],
            'dps': int(top_dps.iloc[0]['target_dps'])
        },
        'most_active_profession': prof_stats.iloc[0]['profession'],
        'average_session_size': round(total_performances / unique_sessions, 1)
    }
    
    with open(output_path / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    conn.close()
    
    print(f"Reports exported to {output_path}/")
    print(f"  - profession_stats.csv")
    print(f"  - top_dps_performers.csv") 
    print(f"  - top_damage_performers.csv")
    print(f"  - role_performance.csv")
    print(f"  - summary.json")


def main():
    parser = argparse.ArgumentParser(description='Analyze GW2 player performance data')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('--player', help='Analyze specific player by account name')
    parser.add_argument('--profession-stats', action='store_true', help='Show profession statistics')
    parser.add_argument('--top-performers', type=int, default=10, help='Show top N performers')
    parser.add_argument('--export', action='store_true', help='Export reports to CSV/JSON files')
    parser.add_argument('--output-dir', default='reports', help='Output directory for exports')
    
    args = parser.parse_args()
    
    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1
    
    if args.player:
        # Show specific player stats
        player_data = get_player_stats(args.database, args.player)
        if player_data.empty:
            print(f"No data found for player: {args.player}")
        else:
            print(f"\nPlayer: {args.player}")
            print(f"Total performances: {len(player_data)}")
            print(f"Professions played: {', '.join(player_data['profession'].unique())}")
            print(f"Average DPS: {player_data['target_dps'].mean():.0f}")
            print(f"Best DPS: {player_data['target_dps'].max():.0f}")
            print(f"Recent performances:")
            print(player_data[['timestamp', 'profession', 'target_dps', 'all_damage']].head(10).to_string(index=False))
    
    if args.profession_stats:
        # Show profession statistics
        prof_stats = get_profession_stats(args.database)
        print("\nProfession Statistics:")
        print(prof_stats.to_string(index=False))
    
    if args.top_performers:
        # Show top performers
        top_performers = get_top_performers(args.database, 'target_dps', args.top_performers)
        print(f"\nTop {args.top_performers} DPS Performers:")
        print(top_performers[['account_name', 'profession', 'target_dps', 'timestamp']].to_string(index=False))
    
    if args.export:
        export_reports(args.database, args.output_dir)
    
    return 0


if __name__ == '__main__':
    exit(main())