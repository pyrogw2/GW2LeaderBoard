#!/usr/bin/env python3
"""
Simple analysis of GW2 player performance data.
"""

import sqlite3
import argparse
from pathlib import Path
import json
import csv
from collections import defaultdict


def get_profession_stats(db_path: str):
    """Get profession statistics."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            profession,
            COUNT(*) as total_performances,
            COUNT(DISTINCT account_name) as unique_players,
            AVG(target_dps) as avg_target_dps,
            MAX(target_dps) as max_target_dps,
            AVG(all_damage) as avg_all_damage,
            MAX(all_damage) as max_all_damage
        FROM player_performances 
        WHERE target_dps > 0
        GROUP BY profession
        ORDER BY avg_target_dps DESC
    '''
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return results


def get_top_performers(db_path: str, metric: str = 'target_dps', limit: int = 20):
    """Get top performers by a specific metric."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = f'''
        SELECT 
            account_name,
            player_name,
            profession,
            timestamp,
            target_dps,
            all_damage,
            fight_time
        FROM player_performances 
        WHERE {metric} > 0
        ORDER BY {metric} DESC
        LIMIT ?
    '''
    
    cursor.execute(query, (limit,))
    results = cursor.fetchall()
    conn.close()
    
    return results


def get_player_performance(db_path: str, account_name: str):
    """Get a player's performance data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            timestamp,
            profession,
            target_dps,
            all_damage,
            fight_time
        FROM player_performances 
        WHERE account_name = ?
        ORDER BY timestamp DESC
    '''
    
    cursor.execute(query, (account_name,))
    results = cursor.fetchall()
    conn.close()
    
    return results


def export_csv(data, headers, filename):
    """Export data to CSV file."""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(data)


def main():
    parser = argparse.ArgumentParser(description='Analyze GW2 player performance data')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('--player', help='Analyze specific player by account name')
    parser.add_argument('--profession-stats', action='store_true', help='Show profession statistics')
    parser.add_argument('--top-performers', type=int, default=10, help='Show top N performers')
    parser.add_argument('--export', action='store_true', help='Export reports to CSV files')
    
    args = parser.parse_args()
    
    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1
    
    if args.player:
        # Show specific player stats
        player_data = get_player_performance(args.database, args.player)
        if not player_data:
            print(f"No data found for player: {args.player}")
        else:
            print(f"\n=== Player Analysis: {args.player} ===")
            print(f"Total performances: {len(player_data)}")
            
            # Calculate stats
            total_dps = sum(row[2] for row in player_data)
            avg_dps = total_dps / len(player_data) if player_data else 0
            max_dps = max(row[2] for row in player_data) if player_data else 0
            
            professions = set(row[1] for row in player_data)
            print(f"Professions played: {', '.join(professions)}")
            print(f"Average DPS: {avg_dps:.0f}")
            print(f"Best DPS: {max_dps:.0f}")
            
            print(f"\nRecent performances:")
            print(f"{'Timestamp':<14} {'Profession':<15} {'DPS':<8} {'Damage':<10}")
            print("-" * 55)
            for row in player_data[:10]:
                print(f"{row[0]:<14} {row[1]:<15} {row[2]:<8} {row[3]:<10}")
    
    if args.profession_stats:
        # Show profession statistics
        prof_stats = get_profession_stats(args.database)
        print(f"\n=== Profession Statistics ===")
        print(f"{'Profession':<15} {'Performances':<12} {'Players':<8} {'Avg DPS':<8} {'Max DPS':<8}")
        print("-" * 65)
        for row in prof_stats:
            print(f"{row[0]:<15} {row[1]:<12} {row[2]:<8} {row[3]:<8.0f} {row[4]:<8.0f}")
    
    if args.top_performers > 0:
        # Show top performers
        top_performers = get_top_performers(args.database, 'target_dps', args.top_performers)
        print(f"\n=== Top {args.top_performers} DPS Performers ===")
        print(f"{'Account':<25} {'Profession':<15} {'DPS':<8} {'Timestamp':<14}")
        print("-" * 70)
        for row in top_performers:
            print(f"{row[0]:<25} {row[2]:<15} {row[4]:<8} {row[3]:<14}")
    
    if args.export:
        # Export data
        print(f"\n=== Exporting Data ===")
        
        # Export profession stats
        prof_stats = get_profession_stats(args.database)
        prof_headers = ['profession', 'total_performances', 'unique_players', 'avg_target_dps', 'max_target_dps', 'avg_all_damage', 'max_all_damage']
        export_csv(prof_stats, prof_headers, 'profession_stats.csv')
        print("Exported profession_stats.csv")
        
        # Export top performers
        top_performers = get_top_performers(args.database, 'target_dps', 50)
        top_headers = ['account_name', 'player_name', 'profession', 'timestamp', 'target_dps', 'all_damage', 'fight_time']
        export_csv(top_performers, top_headers, 'top_performers.csv')
        print("Exported top_performers.csv")
        
        # Create summary
        conn = sqlite3.connect(args.database)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM player_performances')
        total_performances = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT account_name) FROM player_performances')
        unique_players = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT timestamp) FROM player_performances')
        unique_sessions = cursor.fetchone()[0]
        
        summary = {
            'total_performances': total_performances,
            'unique_players': unique_players,
            'unique_sessions': unique_sessions,
            'average_session_size': round(total_performances / unique_sessions, 1) if unique_sessions > 0 else 0
        }
        
        with open('summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        print("Exported summary.json")
        
        conn.close()
    
    return 0


if __name__ == '__main__':
    exit(main())