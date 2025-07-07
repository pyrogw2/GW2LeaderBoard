#!/usr/bin/env python3
"""
Comprehensive GW2 WvW Leaderboard Workflow Script

Handles the complete pipeline from configuration to web UI generation:
1. Configuration management (create if missing)
2. Log download and extraction
3. Log parsing
4. Glicko rating calculation (rebuild-history or incremental)
5. Web UI generation

Common usage:
    python workflow.py                    # Full pipeline with prompts
    python workflow.py --auto-confirm    # Full pipeline without prompts
    python workflow.py --latest-only     # Download only latest log and process
    python workflow.py --parse-only      # Only parse existing logs
    python workflow.py --ui-only         # Only generate web UI
"""

import json
import argparse
import sys
import os
import sqlite3
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import main functions from the respective modules
from gw2_leaderboard.utils.sync_logs import main as sync_logs_main
from gw2_leaderboard.parsers.parse_logs_enhanced import main as parse_logs_enhanced_main
from gw2_leaderboard.core.glicko_rating_system import main as glicko_rating_system_main
from gw2_leaderboard.web.generate_web_ui import main as generate_web_ui_main
from gw2_leaderboard.core.guild_manager import main as guild_manager_main

CONFIG_FILE = "sync_config.json"

DEFAULT_CONFIG = {
    "log_aggregate_url": "https://pyrogw2.github.io",
    "database_path": "gw2_comprehensive.db",
    "extracted_logs_dir": "extracted_logs",
    "web_ui_output": "web_ui_output",
    "auto_confirm": False,
    "max_logs_per_run": 5,
    "guild": {
        "api_key": "",
        "guild_id": "",
        "guild_name": "",
        "guild_tag": "",
        "filter_enabled": False,
        "member_cache_hours": 6
    }
}


def print_header():
    """Print script header with current timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 60)
    print("🚀 GW2 WvW Leaderboard Workflow")
    print(f"📅 Started: {timestamp}")
    print("=" * 60)


def print_step(step: str, description: str):
    """Print a workflow step."""
    print(f"\n📋 Step: {step}")
    print(f"   {description}")
    print("-" * 40)


def load_config() -> Dict:
    """Load configuration from file."""
    if not os.path.exists(CONFIG_FILE):
        return None
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Merge with defaults for any missing keys
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
            elif isinstance(value, dict) and isinstance(config[key], dict):
                for subkey, subvalue in value.items():
                    if subkey not in config[key]:
                        config[key][subkey] = subvalue
        
        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None


def create_config_interactive() -> Dict:
    """Interactively create a new configuration."""
    print("\n🔧 Configuration Setup")
    print("=" * 30)
    
    config = DEFAULT_CONFIG.copy()
    
    # Basic settings
    print("\n📁 Basic Settings:")
    log_url = input(f"Log aggregate URL [{config['log_aggregate_url']}]: ").strip()
    if log_url:
        config['log_aggregate_url'] = log_url
    
    db_name = input(f"Database filename [{config['database_path']}]: ").strip()
    if db_name:
        config['database_path'] = db_name
    
    web_output = input(f"Web UI output directory [{config['web_ui_output']}]: ").strip()
    if web_output:
        config['web_ui_output'] = web_output
    
    max_logs = input(f"Max logs per run [{config['max_logs_per_run']}]: ").strip()
    if max_logs and max_logs.isdigit():
        config['max_logs_per_run'] = int(max_logs)
    
    # Guild settings
    print("\n🛡️  Guild Settings:")
    guild_enabled = input("Enable guild filtering? (y/N): ").strip().lower()
    
    if guild_enabled in ['y', 'yes']:
        config['guild']['filter_enabled'] = True
        config['guild']['api_key'] = input("GW2 API Key: ").strip()
        config['guild']['guild_id'] = input("Guild ID: ").strip()
        config['guild']['guild_name'] = input("Guild Name: ").strip()
        config['guild']['guild_tag'] = input("Guild Tag: ").strip()
        
        cache_hours = input(f"Member cache hours [{config['guild']['member_cache_hours']}]: ").strip()
        if cache_hours and cache_hours.isdigit():
            config['guild']['member_cache_hours'] = int(cache_hours)
    else:
        config['guild']['filter_enabled'] = False
    
    # Save configuration
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return None
    
    return config


def check_database_history(db_path: str) -> bool:
    """Check if rating history exists in the database."""
    if not os.path.exists(db_path):
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if player_rating_history table exists and has data
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='player_rating_history'
        """)
        
        if not cursor.fetchone():
            conn.close()
            return False
        
        cursor.execute("SELECT COUNT(*) FROM player_rating_history")
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    except Exception as e:
        print(f"⚠️  Warning: Could not check database history: {e}")
        return False


def download_and_extract_logs(config: Dict, latest_only: bool = False) -> bool:
    """Download and extract logs using sync_logs.py."""
    print_step("1", "Downloading and extracting logs")
    
    # Prepare arguments for sync_logs_main
    sys_argv_backup = sys.argv[:]
    sys.argv = ['sync_logs.py']
    if latest_only:
        sys.argv.append('--max-logs')
        sys.argv.append('1')
    sys.argv.append('--download-only')
    sys.argv.append('--auto-confirm')
    
    try:
        sync_logs_main()
        success = True
    except SystemExit as e:
        success = (e.code == 0)
    finally:
        sys.argv = sys_argv_backup
    
    return success


def parse_logs(config: Dict) -> bool:
    """Parse logs using parse_logs_enhanced.py."""
    print_step("2", "Parsing extracted logs")
    
    extracted_dir = config['extracted_logs_dir']
    db_path = config['database_path']
    
    if not os.path.exists(extracted_dir):
        print(f"❌ Extracted logs directory '{extracted_dir}' not found")
        return False
    
    # Prepare arguments for parse_logs_enhanced_main
    sys_argv_backup = sys.argv[:]
    sys.argv = ['parse_logs_enhanced.py', extracted_dir, '-d', db_path]
    
    try:
        parse_logs_enhanced_main()
        success = True
    except SystemExit as e:
        success = (e.code == 0)
    finally:
        sys.argv = sys_argv_backup
    
    return success


def update_glicko_ratings(config: Dict, force_rebuild: bool = False) -> bool:
    """Update Glicko ratings using appropriate method."""
    print_step("3", "Updating Glicko ratings")
    
    db_path = config['database_path']
    has_history = check_database_history(db_path)
    
    method = ""
    description = ""
    if force_rebuild or not has_history:
        method = "rebuild-history"
        description = "Rebuilding complete rating history"
        print(f"📊 {description} (this may take a few minutes...)")
    else:
        method = "incremental"
        description = "Incremental rating update"
        print(f"📊 {description}")
    
    # Prepare arguments for glicko_rating_system_main
    sys_argv_backup = sys.argv[:]
    sys.argv = ['glicko_rating_system.py', db_path, f'--{method}']
    
    try:
        glicko_rating_system_main()
        success = True
    except SystemExit as e:
        success = (e.code == 0)
    finally:
        sys.argv = sys_argv_backup
    
    return success


def generate_web_ui(config: Dict) -> bool:
    """Generate web UI using generate_web_ui.py."""
    print_step("4", "Generating web UI")
    
    db_path = config['database_path']
    output_dir = config['web_ui_output']
    
    # Prepare arguments for generate_web_ui_main
    sys_argv_backup = sys.argv[:]
    # Use all 4 date filters with ultra-fast mode
    sys.argv = ['generate_web_ui.py', db_path, '-o', output_dir, '--skip-recalc', 
                '--date-filters', '30d', '60d', '90d', 'overall']
    
    try:
        generate_web_ui_main()
        success = True
    except SystemExit as e:
        success = (e.code == 0)
    finally:
        sys.argv = sys_argv_backup
    
    return success


def main():
    """Main workflow orchestrator."""
    parser = argparse.ArgumentParser(description='GW2 WvW Leaderboard Workflow')
    parser.add_argument('--auto-confirm', action='store_true',
                        help='Skip confirmation prompts')
    parser.add_argument('--latest-only', action='store_true',
                        help='Download only the latest log')
    parser.add_argument('--download-only', action='store_true',
                        help='Only download and extract logs')
    parser.add_argument('--parse-only', action='store_true',
                        help='Only parse existing logs')
    parser.add_argument('--glicko-only', action='store_true',
                        help='Only update Glicko ratings')
    parser.add_argument('--ui-only', action='store_true',
                        help='Only generate web UI')
    parser.add_argument('--force-rebuild', action='store_true',
                        help='Force complete rating history rebuild')
    parser.add_argument('--config-only', action='store_true',
                        help='Only create/update configuration')
    
    args = parser.parse_args()
    
    print_header()
    
    # Load or create configuration
    config = load_config()
    if config is None:
        print("📝 No configuration found. Creating new configuration...")
        config = create_config_interactive()
        if config is None:
            print("❌ Failed to create configuration. Exiting.")
            return 1
    else:
        print("✅ Configuration loaded successfully")
        if args.config_only:
            print("🔧 Updating configuration...")
            config = create_config_interactive()
            if config is None:
                print("❌ Failed to update configuration. Exiting.")
                return 1
            return 0
    
    # Apply auto-confirm from args
    if args.auto_confirm:
        config['auto_confirm'] = True
    
    # Show configuration summary
    print(f"\n📋 Configuration Summary:")
    print(f"   Database: {config['database_path']}")
    print(f"   Logs URL: {config['log_aggregate_url']}")
    print(f"   Web UI Output: {config['web_ui_output']}")
    print(f"   Guild Filtering: {'Enabled' if config['guild']['filter_enabled'] else 'Disabled'}")
    if config['guild']['filter_enabled']:
        print(f"   Guild: {config['guild']['guild_name']} [{config['guild']['guild_tag']}]")
        
        # Optional: Refresh guild members
        if not config.get('auto_confirm', False):
            refresh = input("🔄 Refresh guild members now? (y/N): ").strip().lower()
            if refresh in ['y', 'yes']:
                print_step("🛡️ ", "Refreshing guild members")
                sys_argv_backup = sys.argv[:]
                sys.argv = ['guild_manager.py', '--sync', '--force']
                try:
                    guild_manager_main()
                except SystemExit as e:
                    if e.code != 0:
                        print("❌ Guild member refresh failed.")
                finally:
                    sys.argv = sys_argv_backup
    
    # Determine what operations to run
    operations = []
    
    if args.config_only:
        return 0
    elif args.download_only:
        operations = ['download']
    elif args.parse_only:
        operations = ['parse']
    elif args.glicko_only:
        operations = ['glicko']
    elif args.ui_only:
        operations = ['ui']
    else:
        # Full pipeline
        operations = ['download', 'parse', 'glicko', 'ui']
    
    # Confirmation prompt
    if not config.get('auto_confirm', False):
        operation_desc = " → ".join(operations)
        latest_desc = " (latest log only)" if args.latest_only else ""
        rebuild_desc = " (force rebuild)" if args.force_rebuild else ""
        
        print(f"\n🎯 Operations to run: {operation_desc}{latest_desc}{rebuild_desc}")
        confirm = input("\nProceed? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("🛑 Operation cancelled by user")
            return 0
    
    # Execute operations
    success_count = 0
    total_operations = len(operations)
    
    start_time = datetime.now()
    
    try:
        if 'download' in operations:
            if download_and_extract_logs(config, args.latest_only):
                success_count += 1
            else:
                print("⚠️  Download failed, but continuing with remaining operations...")
        
        if 'parse' in operations:
            if parse_logs(config):
                success_count += 1
            else:
                print("❌ Parse failed. Stopping workflow.")
                return 1
        
        if 'glicko' in operations:
            if update_glicko_ratings(config, args.force_rebuild):
                success_count += 1
            else:
                print("❌ Glicko rating update failed. Stopping workflow.")
                return 1
        
        if 'ui' in operations:
            if generate_web_ui(config):
                success_count += 1
            else:
                print("❌ Web UI generation failed.")
                return 1
    
    except KeyboardInterrupt:
        print("\n\n🛑 Workflow interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print("📊 Workflow Summary")
    print("=" * 60)
    print(f"⏱️  Duration: {duration}")
    print(f"✅ Successful operations: {success_count}/{total_operations}")
    
    if success_count == total_operations:
        print("🎉 All operations completed successfully!")
        if 'ui' in operations:
            print(f"🌐 Web UI available at: {config['web_ui_output']}/index.html")
        return 0
    else:
        print("⚠️  Some operations failed. Check the output above for details.")
        return 1


if __name__ == '__main__':
    exit(main())