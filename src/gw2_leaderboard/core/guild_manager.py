#!/usr/bin/env python3
"""
Guild member management for GW2 API integration.
Handles fetching, caching, and validating guild members.
"""

import json
import sqlite3
import requests
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class GuildManager:
    """Manages guild member data from GW2 API."""
    
    def __init__(self, config_path: str = "sync_config.json"):
        """Initialize with configuration."""
        self.config = self._load_config(config_path)
        self.guild_config = self.config.get("guild", {})
        self.db_path = self.config.get("database_path", "gw2_comprehensive.db")
        
        # GW2 API configuration
        self.api_key = self.guild_config.get("api_key")
        self.guild_id = self.guild_config.get("guild_id")
        self.guild_name = self.guild_config.get("guild_name", "Unknown")
        self.guild_tag = self.guild_config.get("guild_tag", "UNK")
        self.cache_hours = self.guild_config.get("member_cache_hours", 6)
        
        if not self.api_key or not self.guild_id:
            raise ValueError("Guild API key and guild ID must be configured")
        
        self._ensure_guild_table()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load guild configuration from sync_config.json."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get("guild", {})
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Could not load guild config from {config_path}: {e}")
            return {}
    
    def _ensure_guild_table(self):
        """Create guild_members table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS guild_members (
                account_name TEXT PRIMARY KEY,
                guild_rank TEXT,
                joined_date TEXT,
                wvw_member INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def fetch_guild_members(self) -> List[Dict]:
        """Fetch guild members from GW2 API."""
        url = f"https://api.guildwars2.com/v2/guild/{self.guild_id}/members"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            logger.info(f"Fetching guild members for {self.guild_name} ({self.guild_tag})")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            members = response.json()
            logger.info(f"Successfully fetched {len(members)} guild members")
            return members
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch guild members: {e}")
            raise
    
    def update_guild_members_table(self, force_update: bool = False) -> int:
        """Update guild members table from API if cache is stale."""
        if not force_update and not self._cache_is_stale():
            logger.info("Guild member cache is fresh, skipping update")
            return self.get_member_count()
        
        try:
            members = self.fetch_guild_members()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing members
            cursor.execute("DELETE FROM guild_members")
            
            # Insert new members
            for member in members:
                cursor.execute('''
                    INSERT INTO guild_members (account_name, guild_rank, joined_date, wvw_member, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    member["name"],
                    member["rank"],
                    member.get("joined"),
                    1 if member.get("wvw_member", False) else 0,
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated guild members table with {len(members)} members")
            return len(members)
            
        except Exception as e:
            logger.error(f"Failed to update guild members table: {e}")
            raise
    
    def _cache_is_stale(self) -> bool:
        """Check if guild member cache needs refreshing."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(last_updated) FROM guild_members")
        result = cursor.fetchone()
        conn.close()
        
        if not result[0]:
            return True  # No data, needs update
        
        last_updated = datetime.fromisoformat(result[0])
        cache_threshold = datetime.now() - timedelta(hours=self.cache_hours)
        
        return last_updated < cache_threshold
    
    def is_guild_member(self, account_name: str) -> bool:
        """Check if account is a guild member."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM guild_members WHERE account_name = ?", (account_name,))
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def get_guild_members(self) -> Set[str]:
        """Get set of all guild member account names."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT account_name FROM guild_members")
        members = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        return members
    
    def get_member_count(self) -> int:
        """Get current number of cached guild members."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM guild_members")
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_guild_stats(self) -> Dict:
        """Get guild statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get member count and cache info
        cursor.execute("SELECT COUNT(*), MAX(last_updated) FROM guild_members")
        count, last_updated = cursor.fetchone()
        
        # Get players in database who are guild members
        cursor.execute('''
            SELECT COUNT(DISTINCT p.account_name)
            FROM player_performances p
            INNER JOIN guild_members g ON p.account_name = g.account_name
        ''')
        active_members = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "guild_name": self.guild_name,
            "guild_tag": self.guild_tag,
            "total_members": count,
            "active_in_raids": active_members,
            "last_updated": last_updated,
            "cache_stale": self._cache_is_stale()
        }


def main():
    """CLI interface for guild management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage guild member data")
    parser.add_argument("--sync", action="store_true", help="Sync guild members from API")
    parser.add_argument("--force", action="store_true", help="Force update even if cache is fresh")
    parser.add_argument("--stats", action="store_true", help="Show guild statistics")
    parser.add_argument("--check", type=str, help="Check if account is guild member")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        guild_manager = GuildManager()
        
        if args.sync:
            count = guild_manager.update_guild_members_table(force_update=args.force)
            print(f"✅ Synced {count} guild members")
        
        if args.stats:
            stats = guild_manager.get_guild_stats()
            print(f"\n📊 Guild Statistics:")
            print(f"   Guild: {stats['guild_name']} [{stats['guild_tag']}]")
            print(f"   Total Members: {stats['total_members']}")
            print(f"   Active in Raids: {stats['active_in_raids']}")
            print(f"   Last Updated: {stats['last_updated']}")
            print(f"   Cache Status: {'Stale' if stats['cache_stale'] else 'Fresh'}")
        
        if args.check:
            is_member = guild_manager.is_guild_member(args.check)
            status = "✅ Guild Member" if is_member else "❌ Not Guild Member"
            print(f"{args.check}: {status}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())