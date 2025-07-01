#!/usr/bin/env python3
"""
Generate static web UI for GW2 WvW Leaderboards.
Creates HTML/CSS/JS interface that can be uploaded to GitHub Pages.
"""

import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import sys
import os

# Add current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from glicko_rating_system import (
    PROFESSION_METRICS, 
    recalculate_all_glicko_ratings,
    recalculate_profession_ratings
)


def get_glicko_leaderboard_data(db_path: str, metric_category: str = None, limit: int = 100, date_filter: str = None):
    """Extract leaderboard data from database."""
    if date_filter:
        # For date filtering, we need to recalculate ratings on filtered data
        # This is more complex but gives accurate results
        return get_filtered_leaderboard_data(db_path, metric_category, limit, date_filter)
    
    # No date filter - use existing glicko_ratings table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if metric_category and metric_category != "Overall":
        # Specific metric category
        cursor.execute('''
            SELECT account_name, profession, composite_score, rating, games_played, 
                   average_rank, average_stat_value
            FROM glicko_ratings 
            WHERE metric_category = ?
            ORDER BY composite_score DESC
            LIMIT ?
        ''', (metric_category, limit))
    else:
        # Overall leaderboard
        cursor.execute('''
            SELECT account_name, profession, 
                   AVG(composite_score) as avg_composite,
                   AVG(rating) as avg_rating,
                   SUM(games_played) as total_games,
                   AVG(average_rank) as avg_rank,
                   AVG(average_stat_value) as avg_stat
            FROM glicko_ratings
            GROUP BY account_name, profession
            ORDER BY avg_composite DESC
            LIMIT ?
        ''', (limit,))
    
    results = cursor.fetchall()
    conn.close()
    return results


def get_filtered_leaderboard_data(db_path: str, metric_category: str, limit: int, date_filter: str):
    """Get leaderboard data filtered by date - recalculates ratings on filtered data."""
    from glicko_rating_system import parse_date_filter
    import statistics
    
    cutoff_date = parse_date_filter(date_filter)
    if not cutoff_date:
        return get_glicko_leaderboard_data(db_path, metric_category, limit, None)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    if metric_category and metric_category != "Overall":
        # Get filtered performance data for specific metric
        metric_map = {
            'DPS': 'target_dps',
            'Healing': 'healing_per_sec', 
            'Barrier': 'barrier_per_sec',
            'Cleanses': 'condition_cleanses_per_sec',
            'Strips': 'boon_strips_per_sec',
            'Stability': 'stability_gen_per_sec',
            'Resistance': 'resistance_gen_per_sec',
            'Might': 'might_gen_per_sec',
            'Downs': 'down_contribution_per_sec'
        }
        
        if metric_category in metric_map:
            metric_col = metric_map[metric_category]
            
            # Get all sessions for ranking calculation
            cursor.execute(f'''
                SELECT timestamp, account_name, profession, {metric_col}
                FROM player_performances 
                WHERE parsed_date >= ? AND {metric_col} > 0
                ORDER BY timestamp
            ''', (cutoff_date.isoformat(),))
            
            session_data = cursor.fetchall()
            
            # Group by timestamp (session) and calculate ranks
            sessions = {}
            for timestamp, account, profession, stat_value in session_data:
                if timestamp not in sessions:
                    sessions[timestamp] = []
                sessions[timestamp].append((account, profession, stat_value))
            
            # Calculate ranks for each player across all sessions
            player_ranks = {}
            for timestamp, session_players in sessions.items():
                if len(session_players) < 2:
                    continue
                    
                # Sort by stat value (descending for better rank)
                session_players.sort(key=lambda x: x[2], reverse=True)
                total_players = len(session_players)
                
                for rank, (account, profession, stat_value) in enumerate(session_players, 1):
                    key = f"{account}_{profession}"
                    if key not in player_ranks:
                        player_ranks[key] = []
                    
                    rank_percent = (rank / total_players) * 100
                    player_ranks[key].append({
                        'rank_percent': rank_percent,
                        'stat_value': stat_value
                    })
            
            # Calculate final results
            formatted_results = []
            for key, ranks in player_ranks.items():
                account, profession = key.split('_', 1)
                games = len(ranks)
                
                if games >= 2:
                    avg_rank_percent = statistics.mean([r['rank_percent'] for r in ranks])
                    avg_stat = statistics.mean([r['stat_value'] for r in ranks])
                    
                    # Simple rating calculation based on average rank
                    rating = 1500 + (50 - avg_rank_percent) * 10  # Better rank = higher rating
                    composite = rating + (50 - avg_rank_percent) * 5  # Bonus for good rank
                    
                    formatted_results.append((account, profession, composite, rating, games, avg_rank_percent, avg_stat))
            
            # Sort by composite score
            formatted_results.sort(key=lambda x: x[2], reverse=True)
            return formatted_results[:limit]
        else:
            return []
    else:
        # Overall leaderboard - simplified approach
        cursor.execute('''
            SELECT account_name, profession,
                   COUNT(*) as games,
                   AVG((target_dps/100 + healing_per_sec + barrier_per_sec + condition_cleanses_per_sec + 
                        boon_strips_per_sec + stability_gen_per_sec + resistance_gen_per_sec + might_gen_per_sec/10) / 8.0) as avg_overall
            FROM player_performances 
            WHERE parsed_date >= ?
            GROUP BY account_name, profession
            HAVING games >= 2
            ORDER BY avg_overall DESC
            LIMIT ?
        ''', (cutoff_date.isoformat(), limit))
        
        results = cursor.fetchall()
        conn.close()
        
        formatted_results = []
        for i, (account, profession, games, avg_overall) in enumerate(results):
            # Normalize rating to reasonable range
            rating = 1400 + (avg_overall * 5)  # Scale down significantly
            rank_percent = ((i + 1) / len(results)) * 100  # Calculate actual rank percent
            formatted_results.append((account, profession, rating, rating, games, rank_percent, avg_overall))
        
        return formatted_results


def generate_all_leaderboard_data(db_path: str) -> Dict[str, Any]:
    """Generate all leaderboard data in JSON format."""
    data = {
        "generated_at": datetime.now().isoformat(),
        "date_filters": {
            "overall": {},
            "30d": {},
            "90d": {},
            "180d": {}
        }
    }
    
    # Individual metric categories
    individual_categories = [
        "DPS", "Healing", "Barrier", "Cleanses", "Strips", 
        "Stability", "Resistance", "Might", "Downs"
    ]
    
    # Date filters to generate
    date_filters = {
        "overall": None,
        "30d": "30d", 
        "90d": "90d",
        "180d": "180d"
    }
    
    # Generate data for each date filter
    for filter_name, filter_value in date_filters.items():
        print(f"\nGenerating data for {filter_name}...")
        
        filter_data = {
            "individual_metrics": {},
            "profession_leaderboards": {},
            "overall_leaderboard": []
        }
        
        print("  Individual metric leaderboards...")
        for category in individual_categories:
            print(f"    Processing {category}...")
            results = get_glicko_leaderboard_data(db_path, category, limit=100, date_filter=filter_value)
            filter_data["individual_metrics"][category] = [
                {
                    "rank": i + 1,
                    "account_name": account,
                    "profession": profession,
                    "composite_score": float(composite),
                    "glicko_rating": float(rating),
                    "games_played": int(games),
                    "average_rank_percent": float(avg_rank) if avg_rank > 0 else None,
                    "average_stat_value": float(avg_stat) if avg_stat > 0 else None
                }
                for i, (account, profession, composite, rating, games, avg_rank, avg_stat) in enumerate(results)
            ]
        
        # Overall leaderboard
        print("  Overall leaderboard...")
        results = get_glicko_leaderboard_data(db_path, "Overall", limit=100, date_filter=filter_value)
        filter_data["overall_leaderboard"] = [
            {
                "rank": i + 1,
                "account_name": account,
                "profession": profession,
                "composite_score": float(composite),
                "glicko_rating": float(rating),
                "games_played": int(games),
                "average_rank_percent": float(avg_rank) if avg_rank > 0 else None,
                "average_stat_value": float(avg_stat) if avg_stat > 0 else None
            }
            for i, (account, profession, composite, rating, games, avg_rank, avg_stat) in enumerate(results)
        ]
        
        # Profession-specific leaderboards
        print("  Profession-specific leaderboards...")
        for profession in PROFESSION_METRICS.keys():
            print(f"    Processing {profession}...")
            try:
                results = recalculate_profession_ratings(db_path, profession, date_filter=filter_value)
                if results:
                    prof_config = PROFESSION_METRICS[profession]
                    filter_data["profession_leaderboards"][profession] = {
                        "metrics": prof_config["metrics"],
                        "weights": prof_config["weights"],
                        "players": [
                            {
                                "rank": i + 1,
                                "account_name": account,
                                "composite_score": float(composite),
                                "glicko_rating": float(rating),
                                "games_played": int(games),
                                "average_rank_percent": float(avg_rank) if avg_rank > 0 else None,
                                "key_stats": stats_breakdown
                            }
                            for i, (account, rating, games, avg_rank, composite, stats_breakdown) in enumerate(results[:100])
                        ]
                    }
            except Exception as e:
                print(f"      Error processing {profession}: {e}")
                continue
        
        data["date_filters"][filter_name] = filter_data
    
    return data


def generate_html_ui(data: Dict[str, Any], output_dir: Path):
    """Generate the HTML UI files."""
    output_dir.mkdir(exist_ok=True)
    
    # Generate main HTML file
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GW2 WvW Leaderboards</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>🏆 GW2 WvW Leaderboards</h1>
            <p class="subtitle">Glicko-based rating system for World vs World performance</p>
            <p class="last-updated">Last updated: <span id="lastUpdated"></span></p>
        </header>

        <nav class="nav-tabs">
            <button class="tab-button active" data-tab="individual">Individual Metrics</button>
            <button class="tab-button" data-tab="professions">Professions</button>
            <button class="tab-button" data-tab="about">About</button>
        </nav>

        <div class="date-filters">
            <span class="filter-label">Time Period:</span>
            <button class="date-filter-button active" data-filter="overall">All Time</button>
            <button class="date-filter-button" data-filter="30d">Last 30 Days</button>
            <button class="date-filter-button" data-filter="90d">Last 90 Days</button>
            <button class="date-filter-button" data-filter="180d">Last 180 Days</button>
        </div>

        <main>
            <!-- Individual Metrics -->
            <div id="individual" class="tab-content active">
                <h2>Individual Metrics</h2>
                <p class="description">Rankings by specific performance metrics.</p>
                
                <div class="metric-selector">
                    <button class="metric-button active" data-metric="DPS">DPS</button>
                    <button class="metric-button" data-metric="Healing">Healing</button>
                    <button class="metric-button" data-metric="Barrier">Barrier</button>
                    <button class="metric-button" data-metric="Cleanses">Cleanses</button>
                    <button class="metric-button" data-metric="Strips">Strips</button>
                    <button class="metric-button" data-metric="Stability">Stability</button>
                    <button class="metric-button" data-metric="Resistance">Resistance</button>
                    <button class="metric-button" data-metric="Might">Might</button>
                    <button class="metric-button" data-metric="Downs">DownCont</button>
                </div>
                
                <div id="individual-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- Profession Leaderboards -->
            <div id="professions" class="tab-content">
                <h2>Profession Leaderboards</h2>
                <p class="description">Role-specific rankings with weighted metrics for each profession.</p>
                
                <div class="profession-selector">
                    <button class="profession-button active" data-profession="Firebrand">Firebrand</button>
                    <button class="profession-button" data-profession="Chronomancer">Chronomancer</button>
                    <button class="profession-button" data-profession="Scourge">Scourge</button>
                    <button class="profession-button" data-profession="Druid">Druid</button>
                    <button class="profession-button" data-profession="Condi Firebrand">Condi Firebrand</button>
                    <button class="profession-button" data-profession="Support Spb">Support Spb</button>
                </div>
                
                <div id="profession-info" class="profession-info"></div>
                <div id="profession-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- About -->
            <div id="about" class="tab-content">
                <h2>About the Rating System</h2>
                <div class="about-content">
                    <h3>🎯 Methodology</h3>
                    <p>This leaderboard uses a <strong>Glicko rating system</strong> combined with session-based z-score evaluation to rank World vs World performance.</p>
                    
                    <h3>📊 How It Works</h3>
                    <ul>
                        <li><strong>Session-Based Evaluation:</strong> Each combat session is analyzed independently</li>
                        <li><strong>Z-Score Calculation:</strong> Player performance is compared to others in the same session</li>
                        <li><strong>Glicko Rating:</strong> Dynamic rating system that accounts for uncertainty and volatility</li>
                        <li><strong>Composite Scoring:</strong> Combines Glicko rating with average rank performance</li>
                    </ul>
                    
                    <h3>🏅 Leaderboard Types</h3>
                    <ul>
                        <li><strong>Overall:</strong> Combined ranking across all metrics</li>
                        <li><strong>Individual Metrics:</strong> Specialized rankings for DPS, healing, support, etc.</li>
                        <li><strong>Profession-Specific:</strong> Role-based rankings with weighted metrics</li>
                    </ul>
                    
                    <h3>📈 Key Metrics</h3>
                    <ul>
                        <li><strong>Composite Score:</strong> Final ranking score combining multiple factors</li>
                        <li><strong>Glicko Rating:</strong> Base skill rating (higher = better)</li>
                        <li><strong>Avg Rank%:</strong> Average percentile rank in sessions (lower = better)</li>
                        <li><strong>Games:</strong> Number of combat sessions analyzed</li>
                    </ul>
                </div>
            </div>
        </main>
    </div>

    <script src="script.js"></script>
</body>
</html>"""

    # Generate CSS file
    css_content = """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    text-align: center;
    margin-bottom: 30px;
    color: white;
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 10px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

.subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    margin-bottom: 10px;
}

.last-updated {
    font-size: 0.9rem;
    opacity: 0.8;
}

.nav-tabs {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
    background: rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 10px;
    backdrop-filter: blur(10px);
}

.date-filters {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 30px;
    background: rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 15px;
    backdrop-filter: blur(10px);
    flex-wrap: wrap;
    gap: 10px;
}

.filter-label {
    color: white;
    font-weight: bold;
    margin-right: 15px;
    font-size: 1rem;
}

.date-filter-button {
    background: rgba(255,255,255,0.2);
    border: 2px solid rgba(255,255,255,0.3);
    padding: 8px 16px;
    border-radius: 6px;
    color: white;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.date-filter-button:hover {
    background: rgba(255,255,255,0.3);
    border-color: rgba(255,255,255,0.5);
}

.date-filter-button.active {
    background: rgba(255,255,255,0.4);
    border-color: rgba(255,255,255,0.6);
    font-weight: bold;
}

.tab-button {
    background: transparent;
    border: none;
    padding: 12px 24px;
    margin: 0 5px;
    border-radius: 8px;
    color: white;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.tab-button:hover {
    background: rgba(255,255,255,0.2);
}

.tab-button.active {
    background: rgba(255,255,255,0.3);
    font-weight: bold;
}

main {
    background: white;
    border-radius: 15px;
    padding: 30px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    min-height: 600px;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

h2 {
    color: #333;
    margin-bottom: 10px;
    font-size: 1.8rem;
}

.description {
    color: #666;
    margin-bottom: 25px;
    font-size: 1.1rem;
}

.metric-selector, .profession-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 25px;
    justify-content: center;
}

.metric-button, .profession-button {
    background: #f8f9fa;
    border: 2px solid #dee2e6;
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.9rem;
}

.metric-button:hover, .profession-button:hover {
    background: #e9ecef;
    border-color: #adb5bd;
}

.metric-button.active, .profession-button.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.profession-info {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    border-left: 4px solid #667eea;
}

.profession-info h3 {
    margin-bottom: 10px;
    color: #333;
}

.profession-info p {
    color: #666;
    margin-bottom: 5px;
}

.leaderboard-container {
    overflow-x: auto;
}

.leaderboard-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.leaderboard-table th,
.leaderboard-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #dee2e6;
}

.leaderboard-table th {
    background: #f8f9fa;
    font-weight: bold;
    color: #495057;
    position: sticky;
    top: 0;
}

.leaderboard-table tr:hover {
    background: #f8f9fa;
}

.rank-cell {
    font-weight: bold;
    color: #667eea;
    width: 60px;
}

.account-cell {
    font-weight: 500;
    min-width: 200px;
}

.profession-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
    text-transform: uppercase;
    margin-left: 10px;
    gap: 4px;
    white-space: nowrap;
}

.profession-icon {
    width: 16px;
    height: 16px;
    border-radius: 2px;
}

.stat-value {
    font-family: 'Courier New', monospace;
    font-weight: bold;
}

.rank-percent {
    color: #28a745;
    font-weight: bold;
}

.rank-percent.poor {
    color: #dc3545;
}

.rank-percent.average {
    color: #ffc107;
}

.raids-value {
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 3px;
}

.about-content {
    line-height: 1.8;
}

.about-content h3 {
    color: #667eea;
    margin: 25px 0 15px 0;
    font-size: 1.3rem;
}

.about-content ul {
    margin-left: 20px;
    margin-bottom: 20px;
}

.about-content li {
    margin-bottom: 8px;
}

.about-content strong {
    color: #333;
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    header h1 {
        font-size: 2rem;
    }
    
    .nav-tabs {
        flex-wrap: wrap;
        gap: 5px;
    }
    
    .tab-button {
        padding: 10px 16px;
        font-size: 0.9rem;
    }
    
    main {
        padding: 20px;
    }
    
    .metric-selector, .profession-selector {
        justify-content: flex-start;
    }
    
    .metric-button, .profession-button {
        padding: 8px 16px;
        font-size: 0.8rem;
    }
    
    .leaderboard-table th,
    .leaderboard-table td {
        padding: 8px;
        font-size: 0.9rem;
    }
    
    .account-cell {
        min-width: 150px;
    }
}"""

    # Generate JavaScript file
    js_content = f"""// Leaderboard data
const leaderboardData = {json.dumps(data, indent=2)};

// Current state
let currentDateFilter = 'overall';
let currentTab = 'individual';
let currentMetric = 'DPS';
let currentProfession = 'Firebrand';

// GW2 Wiki profession icons
const professionIcons = {{
    'Guardian': 'https://wiki.guildwars2.com/images/c/c7/Guardian_icon_small.png',
    'Dragonhunter': 'https://wiki.guildwars2.com/images/5/5d/Dragonhunter_icon_small.png',
    'Firebrand': 'https://wiki.guildwars2.com/images/0/0e/Firebrand_icon_small.png',
    'Willbender': 'https://wiki.guildwars2.com/images/c/c7/Guardian_icon_small.png', // Fallback to Guardian
    'Warrior': 'https://wiki.guildwars2.com/images/4/45/Warrior_icon_small.png',
    'Berserker': 'https://wiki.guildwars2.com/images/a/a8/Berserker_icon_small.png',
    'Spellbreaker': 'https://wiki.guildwars2.com/images/0/08/Spellbreaker_icon_small.png',
    'Bladesworn': 'https://wiki.guildwars2.com/images/c/cf/Bladesworn_icon_small.png',
    'Engineer': 'https://wiki.guildwars2.com/images/0/07/Engineer_icon_small.png',
    'Scrapper': 'https://wiki.guildwars2.com/images/7/7d/Scrapper_icon_small.png',
    'Holosmith': 'https://wiki.guildwars2.com/images/a/aa/Holosmith_icon_small.png',
    'Mechanist': 'https://wiki.guildwars2.com/images/6/6d/Mechanist_icon_small.png',
    'Ranger': 'https://wiki.guildwars2.com/images/1/1e/Ranger_icon_small.png',
    'Druid': 'https://wiki.guildwars2.com/images/9/9b/Druid_icon_small.png',
    'Soulbeast': 'https://wiki.guildwars2.com/images/f/f6/Soulbeast_icon_small.png',
    'Untamed': 'https://wiki.guildwars2.com/images/2/2d/Untamed_icon_small.png',
    'Thief': 'https://wiki.guildwars2.com/images/7/7a/Thief_icon_small.png',
    'Daredevil': 'https://wiki.guildwars2.com/images/f/f3/Daredevil_icon_small.png',
    'Deadeye': 'https://wiki.guildwars2.com/images/7/70/Deadeye_icon_small.png',
    'Specter': 'https://wiki.guildwars2.com/images/6/61/Specter_icon_small.png',
    'Elementalist': 'https://wiki.guildwars2.com/images/4/4e/Elementalist_icon_small.png',
    'Tempest': 'https://wiki.guildwars2.com/images/4/4a/Tempest_icon_small.png',
    'Weaver': 'https://wiki.guildwars2.com/images/c/c3/Weaver_icon_small.png',
    'Catalyst': 'https://wiki.guildwars2.com/images/c/c5/Catalyst_icon_small.png',
    'Mesmer': 'https://wiki.guildwars2.com/images/7/79/Mesmer_icon_small.png',
    'Chronomancer': 'https://wiki.guildwars2.com/images/e/e0/Chronomancer_icon_small.png',
    'Mirage': 'https://wiki.guildwars2.com/images/c/c8/Mirage_icon_small.png',
    'Virtuoso': 'https://wiki.guildwars2.com/images/a/a7/Virtuoso_icon_small.png',
    'Necromancer': 'https://wiki.guildwars2.com/images/1/10/Necromancer_icon_small.png',
    'Reaper': 'https://wiki.guildwars2.com/images/9/93/Reaper_icon_small.png',
    'Scourge': 'https://wiki.guildwars2.com/images/e/e8/Scourge_icon_small.png',
    'Harbinger': 'https://wiki.guildwars2.com/images/1/1d/Harbinger_icon_small.png',
    'Revenant': 'https://wiki.guildwars2.com/images/4/4c/Revenant_icon_small.png',
    'Herald': 'https://wiki.guildwars2.com/images/3/39/Herald_icon_small.png',
    'Renegade': 'https://wiki.guildwars2.com/images/b/be/Renegade_icon_small.png',
    'Vindicator': 'https://wiki.guildwars2.com/images/6/6d/Vindicator_icon_small.png',
    'Condi Firebrand': 'https://wiki.guildwars2.com/images/0/0e/Firebrand_icon_small.png',
    'Support Spb': 'https://wiki.guildwars2.com/images/0/08/Spellbreaker_icon_small.png'
}};

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {{
    initializePage();
    setupEventListeners();
    loadCurrentData();
}});

function initializePage() {{
    // Set last updated time
    const lastUpdated = new Date(leaderboardData.generated_at);
    document.getElementById('lastUpdated').textContent = lastUpdated.toLocaleString();
}}

function setupEventListeners() {{
    // Tab navigation
    document.querySelectorAll('.tab-button').forEach(button => {{
        button.addEventListener('click', function() {{
            switchTab(this.dataset.tab);
        }});
    }});
    
    // Date filter selection
    document.querySelectorAll('.date-filter-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectDateFilter(this.dataset.filter);
        }});
    }});
    
    // Metric selection
    document.querySelectorAll('.metric-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectMetric(this.dataset.metric);
        }});
    }});
    
    // Profession selection
    document.querySelectorAll('.profession-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectProfession(this.dataset.profession);
        }});
    }});
}}

function selectDateFilter(filter) {{
    currentDateFilter = filter;
    document.querySelectorAll('.date-filter-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-filter="${{filter}}"]`).classList.add('active');
    loadCurrentData();
}}

function getCurrentData() {{
    return leaderboardData.date_filters[currentDateFilter];
}}

function switchTab(tabName) {{
    currentTab = tabName;
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-tab="${{tabName}}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    
    loadCurrentData();
}}

function selectMetric(metric) {{
    currentMetric = metric;
    document.querySelectorAll('.metric-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-metric="${{metric}}"]`).classList.add('active');
    if (currentTab === 'individual') {{
        loadIndividualMetric(metric);
    }}
}}

function selectProfession(profession) {{
    currentProfession = profession;
    document.querySelectorAll('.profession-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-profession="${{profession}}"]`).classList.add('active');
    if (currentTab === 'professions') {{
        loadProfessionLeaderboard(profession);
    }}
}}

function loadCurrentData() {{
    switch(currentTab) {{
        case 'overall':
            loadOverallLeaderboard();
            break;
        case 'individual':
            loadIndividualMetric(currentMetric);
            break;
        case 'professions':
            loadProfessionLeaderboard(currentProfession);
            break;
    }}
}}

function loadOverallLeaderboard() {{
    const container = document.getElementById('overall-leaderboard');
    const data = getCurrentData().overall_leaderboard;
    
    container.innerHTML = createLeaderboardTable(data, [
        {{ key: 'rank', label: 'Rank', type: 'rank' }},
        {{ key: 'account_name', label: 'Account', type: 'account' }},
        {{ key: 'profession', label: 'Profession', type: 'profession' }},
        {{ key: 'composite_score', label: 'Composite', type: 'number' }},
        {{ key: 'glicko_rating', label: 'Glicko', type: 'number' }},
        {{ key: 'games_played', label: 'Raids', type: 'raids' }},
        {{ key: 'average_rank_percent', label: 'Avg Rank%', type: 'percent' }}
    ]);
}}

function loadIndividualMetric(metric) {{
    const container = document.getElementById('individual-leaderboard');
    const data = getCurrentData().individual_metrics[metric];
    
    if (!data) {{
        container.innerHTML = '<p>No data available for this metric.</p>';
        return;
    }}
    
    container.innerHTML = createLeaderboardTable(data, [
        {{ key: 'rank', label: 'Rank', type: 'rank' }},
        {{ key: 'account_name', label: 'Account', type: 'account' }},
        {{ key: 'profession', label: 'Profession', type: 'profession' }},
        {{ key: 'composite_score', label: 'Composite', type: 'number' }},
        {{ key: 'glicko_rating', label: 'Glicko', type: 'number' }},
        {{ key: 'games_played', label: 'Raids', type: 'raids' }},
        {{ key: 'average_rank_percent', label: 'Avg Rank%', type: 'percent' }},
        {{ key: 'average_stat_value', label: `Avg ${{metric}}`, type: 'stat' }}
    ]);
}}

function loadProfessionLeaderboard(profession) {{
    const infoContainer = document.getElementById('profession-info');
    const container = document.getElementById('profession-leaderboard');
    const data = getCurrentData().profession_leaderboards[profession];
    
    if (!data) {{
        infoContainer.innerHTML = '<p>No data available for this profession.</p>';
        container.innerHTML = '';
        return;
    }}
    
    // Show profession info
    const metricsText = data.metrics.join(', ');
    const weightsText = data.weights.map(w => `${{(w * 100).toFixed(0)}}%`).join('/');
    
    infoContainer.innerHTML = `
        <h3>${{profession}} Metrics</h3>
        <p><strong>Weighted Metrics:</strong> ${{metricsText}}</p>
        <p><strong>Weights:</strong> ${{weightsText}}</p>
    `;
    
    // Show leaderboard
    container.innerHTML = createLeaderboardTable(data.players, [
        {{ key: 'rank', label: 'Rank', type: 'rank' }},
        {{ key: 'account_name', label: 'Account', type: 'account' }},
        {{ key: 'composite_score', label: 'Composite', type: 'number' }},
        {{ key: 'glicko_rating', label: 'Glicko', type: 'number' }},
        {{ key: 'games_played', label: 'Raids', type: 'raids' }},
        {{ key: 'key_stats', label: 'Key Stats', type: 'stats' }}
    ]);
}}

function createLeaderboardTable(data, columns) {{
    if (!data || data.length === 0) {{
        return '<p>No data available.</p>';
    }}
    
    let html = '<table class="leaderboard-table"><thead><tr>';
    
    columns.forEach(col => {{
        html += `<th>${{col.label}}</th>`;
    }});
    
    html += '</tr></thead><tbody>';
    
    data.forEach(row => {{
        html += '<tr>';
        columns.forEach(col => {{
            const value = row[col.key];
            html += `<td class="${{col.type}}-cell">${{formatCellValue(value, col.type)}}</td>`;
        }});
        html += '</tr>';
    }});
    
    html += '</tbody></table>';
    
    // Apply raids gradient coloring after table creation
    setTimeout(() => applyRaidsGradient(), 10);
    
    return html;
}}

function formatCellValue(value, type) {{
    if (value === null || value === undefined) {{
        return 'N/A';
    }}
    
    switch (type) {{
        case 'rank':
            return `<span class="rank-cell">#${{value}}</span>`;
        case 'account':
            return `<span class="account-cell">${{value}}</span>`;
        case 'profession':
            const iconUrl = professionIcons[value] || '';
            const iconHtml = iconUrl ? `<img src="${{iconUrl}}" class="profession-icon" alt="${{value}}" onerror="this.style.display='none'">` : '';
            return `${{iconHtml}} ${{value}}`;
        case 'number':
            return Math.round(value);
        case 'raids':
            return `<span class="raids-value" data-raids="${{value}}">${{Math.round(value)}}</span>`;
        case 'percent':
            const percentClass = value < 25 ? 'rank-percent' : value > 75 ? 'rank-percent poor' : 'rank-percent average';
            return `<span class="${{percentClass}}">${{value.toFixed(1)}}%</span>`;
        case 'stat':
            return `<span class="stat-value">${{value.toFixed(1)}}</span>`;
        case 'stats':
            return `<span class="stat-value">${{value}}</span>`;
        default:
            return value;
    }}
}}

function getProfessionColor(profession) {{
    const colors = {{
        'Firebrand': '#e74c3c',
        'Chronomancer': '#9b59b6',
        'Scourge': '#2c3e50',
        'Druid': '#27ae60',
        'Condi Firebrand': '#d35400',
        'Support Spb': '#f39c12',
        'Catalyst': '#3498db',
        'Weaver': '#e67e22',
        'Tempest': '#1abc9c',
        'Holosmith': '#34495e',
        'Dragonhunter': '#f1c40f',
        'Reaper': '#8e44ad',
        'Soulbeast': '#16a085',
        'Untamed': '#c0392b',
        'Spellbreaker': '#7f8c8d',
        'Berserker': '#e74c3c'
    }};
    return colors[profession] || '#95a5a6';
}}

function applyRaidsGradient() {{
    const raidsElements = document.querySelectorAll('.raids-value');
    if (raidsElements.length === 0) return;
    
    // Get all raids values and find min/max
    const raidsValues = Array.from(raidsElements).map(el => parseInt(el.dataset.raids));
    const minRaids = Math.min(...raidsValues);
    const maxRaids = Math.max(...raidsValues);
    
    // Apply gradient coloring
    raidsElements.forEach(element => {{
        const raids = parseInt(element.dataset.raids);
        const ratio = maxRaids === minRaids ? 0.5 : (raids - minRaids) / (maxRaids - minRaids);
        
        // Interpolate between red (0) and green (255)
        const red = Math.round(255 * (1 - ratio));
        const green = Math.round(255 * ratio);
        const blue = 0;
        
        element.style.backgroundColor = `rgba(${{red}}, ${{green}}, ${{blue}}, 0.3)`;
        element.style.color = ratio > 0.5 ? '#2d5a2d' : '#5a2d2d';
    }});
}}"""

    # Write all files
    (output_dir / "index.html").write_text(html_content)
    (output_dir / "styles.css").write_text(css_content)
    (output_dir / "script.js").write_text(js_content)
    
    print(f"HTML UI generated in: {output_dir}")
    print("Files created:")
    print("  - index.html")
    print("  - styles.css") 
    print("  - script.js")


def main():
    parser = argparse.ArgumentParser(description='Generate static web UI for GW2 WvW Leaderboards')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('-o', '--output', default='web_ui', help='Output directory (default: web_ui)')
    parser.add_argument('--skip-recalc', action='store_true', help='Skip recalculating ratings (use existing data)')
    
    args = parser.parse_args()
    
    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1
    
    output_dir = Path(args.output)
    
    # Recalculate ratings first unless skipped
    if not args.skip_recalc:
        print("Recalculating all Glicko ratings...")
        recalculate_all_glicko_ratings(args.database)
        print("Rating recalculation complete!")
    
    print("\nGenerating leaderboard data...")
    data = generate_all_leaderboard_data(args.database)
    
    print("\nGenerating HTML UI...")
    generate_html_ui(data, output_dir)
    
    print(f"\n✅ Web UI generation complete!")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print(f"🌐 Open {output_dir / 'index.html'} in your browser to view")
    print(f"📤 Upload the contents of {output_dir} to GitHub Pages or any web host")
    
    return 0


if __name__ == '__main__':
    exit(main())