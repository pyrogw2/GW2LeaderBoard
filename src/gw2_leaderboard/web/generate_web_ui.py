#!/usr/bin/env python3
"""
Generate static web UI for GW2 WvW Leaderboards.
Creates HTML/CSS/JS interface that can be uploaded to GitHub Pages.

This module has been refactored into a modular structure:
- data_processing.py: Database queries and data processing
- parallel_processing.py: Concurrent data generation and progress tracking  
- templates/: HTML, CSS, and JavaScript template modules
- file_generator.py: Orchestration and file generation
"""

import argparse
import sqlite3
import sys
import os
import json
from pathlib import Path

# Add current directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import modular components
try:
    # Try relative imports (when used as a module)
    from .data_processing import recalculate_all_glicko_ratings
    from .file_generator import generate_complete_web_ui
except ImportError:
    # Fall back to absolute imports (when run directly)
    from data_processing import recalculate_all_glicko_ratings
    from file_generator import generate_complete_web_ui

# Optional guild manager import
try:
    # Try relative import first (when used as a module)
    from ..core.guild_manager import GuildManager
    GUILD_MANAGER_AVAILABLE = True
except ImportError:
    try:
        # Fall back to absolute import (when run directly)
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
        from gw2_leaderboard.core.guild_manager import GuildManager
        GUILD_MANAGER_AVAILABLE = True
    except ImportError:
        GUILD_MANAGER_AVAILABLE = False
        GuildManager = None


def main():
    """Main entry point for web UI generation."""
    parser = argparse.ArgumentParser(description='Generate static web UI for GW2 WvW Leaderboards')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('-o', '--output', help='Output directory for web UI', default='web_ui_output')
    parser.add_argument('--max-workers', type=int, default=4, help='Max workers for parallel processing')
    parser.add_argument('--skip-recalc', action='store_true', help='Skip recalculating Glicko ratings')
    parser.add_argument('--date-filters', nargs='+', default=['30d', '60d', '90d', 'overall'],
                        help='Date filters to generate (default: 30d 60d 90d overall)')

    args = parser.parse_args()

    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1

    output_dir = Path(args.output)

    # Check if glicko_ratings table has data
    conn = sqlite3.connect(args.database)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM glicko_ratings")
    ratings_count = cursor.fetchone()[0]
    
    # Check for guild configuration
    guild_enabled = False
    guild_name = ""
    guild_tag = ""
    
    # First check if guild filtering is enabled in config
    try:
        with open("sync_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        guild_config = config.get("guild", {})
        filter_enabled = guild_config.get("filter_enabled", False)
        
        if filter_enabled and GUILD_MANAGER_AVAILABLE:
            try:
                guild_manager = GuildManager()
                guild_enabled = True
                guild_name = guild_manager.guild_name
                guild_tag = guild_manager.guild_tag
                print(f"Guild filtering enabled: {guild_name} [{guild_tag}]")
            except Exception as e:
                print(f"Could not initialize GuildManager: {e}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Could not load sync_config.json: {e}")

    conn.close()
    
    # Recalculate ratings if needed
    if not args.skip_recalc or ratings_count == 0:
        if ratings_count == 0:
            print("Glicko ratings table is empty - forcing recalculation...")
        else:
            print("Recalculating all Glicko ratings...")
        recalculate_all_glicko_ratings(args.database, guild_filter=guild_enabled)
        print("Rating recalculation complete!")

    # Generate complete web UI using the modular system
    print(f"\nGenerating complete web UI with date filters: {args.date_filters}")
    
    data = generate_complete_web_ui(
        db_path=args.database,
        output_dir=output_dir,
        date_filters=args.date_filters,
        guild_enabled=guild_enabled,
        guild_name=guild_name,
        guild_tag=guild_tag
    )

    print(f"\n✅ Web UI generation complete!")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print(f"🌐 Open {output_dir / 'index.html'} in your browser to view")
    print(f"📤 Upload the contents of {output_dir} to GitHub Pages or any web host")
    
    # Print summary statistics
    total_players = 0
    total_professions = 0
    for filter_name, filter_data in data.get('date_filters', {}).items():
        individual_metrics = filter_data.get('individual_metrics', {})
        if 'DPS' in individual_metrics:
            total_players = max(total_players, len(individual_metrics['DPS']))
        
        profession_leaderboards = filter_data.get('profession_leaderboards', {})
        total_professions = max(total_professions, len(profession_leaderboards))
    
    print(f"📊 Generated data for {total_players} players across {total_professions} professions")
    print(f"🕐 Date filters: {', '.join(args.date_filters)}")
    
    if guild_enabled:
        print(f"🛡️  Guild filtering enabled for {guild_name} [{guild_tag}]")

    return 0


if __name__ == '__main__':
    exit(main())