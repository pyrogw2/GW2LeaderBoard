#!/usr/bin/env python3
"""
Comprehensive player summary generator for GW2 WvW Leaderboards.
Provides detailed analysis of individual player performance across all metrics.
"""

import sqlite3
import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

# Import existing Glicko system for metric mappings
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from .glicko_rating_system import METRIC_CATEGORIES, PROFESSION_METRICS, build_date_filter_clause
except ImportError:
    # Fallback definitions if import fails
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
        'DownCont': 'down_contribution_per_sec'
    }
    
    def build_date_filter_clause(date_filter: str = None):
        """Fallback date filter function"""
        return "", []


@dataclass
class PlayerProfile:
    """Core player profile information."""
    account_name: str
    character_names: List[str]
    professions_played: List[str]
    is_guild_member: bool
    guild_rank: Optional[str]
    total_sessions: int
    first_session: str
    last_session: str
    activity_days: int


@dataclass
class MetricSummary:
    """Summary stats for a specific metric."""
    metric_name: str
    glicko_rating: float
    rating_deviation: float
    games_played: int
    average_value: float
    best_value: float
    worst_value: float
    percentile_rank: float
    overall_rank: int
    total_players: int


@dataclass
class ProfessionSummary:
    """Performance summary for a specific profession."""
    profession: str
    sessions_played: int
    primary_metrics: Dict[str, float]  # Key metrics for this profession
    overall_glicko: float
    best_session: Dict[str, Any]
    recent_trend: str  # "improving", "declining", "stable"
    metric_summaries: List[MetricSummary]  # Detailed metrics for this profession


@dataclass
class SessionSummary:
    """Summary of a single combat session."""
    timestamp: str
    profession: str
    session_rank: int
    total_players: int
    key_stats: Dict[str, float]
    performance_grade: str  # A, B, C, D, F based on z-scores


@dataclass
class PlayerSummary:
    """Complete player analysis summary."""
    profile: PlayerProfile
    overall_stats: Dict[str, Any]
    metric_summaries: List[MetricSummary]
    profession_summaries: List[ProfessionSummary]
    recent_sessions: List[SessionSummary]
    trends: Dict[str, Any]
    rankings: Dict[str, Any]


class PlayerSummaryGenerator:
    """Generates comprehensive player summaries from the database."""
    
    def __init__(self, db_path: str, date_filter: str = None):
        self.db_path = db_path
        self.date_filter = date_filter
        self.date_clause, self.date_params = build_date_filter_clause(date_filter)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_player_profile(self, account_name: str) -> Optional[PlayerProfile]:
        """Get basic player profile information."""
        cursor = self.conn.cursor()
        
        # Get basic player data
        cursor.execute(f"""
            SELECT 
                account_name,
                GROUP_CONCAT(DISTINCT player_name) as character_names,
                GROUP_CONCAT(DISTINCT profession) as professions,
                COUNT(DISTINCT timestamp) as total_sessions,
                MIN(timestamp) as first_session,
                MAX(timestamp) as last_session
            FROM player_performances 
            WHERE account_name = ? {self.date_clause}
            GROUP BY account_name
        """, (account_name,) + tuple(self.date_params))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        # Get guild information
        cursor.execute("""
            SELECT guild_rank, wvw_member 
            FROM guild_members 
            WHERE account_name = ?
        """, (account_name,))
        
        guild_row = cursor.fetchone()
        is_guild_member = guild_row is not None  # If they're in the table, they're a guild member
        guild_rank = guild_row['guild_rank'] if guild_row else None
        
        # Calculate activity days
        if row['first_session'] and row['last_session']:
            first_date = datetime.strptime(row['first_session'][:8], '%Y%m%d')
            last_date = datetime.strptime(row['last_session'][:8], '%Y%m%d')
            activity_days = (last_date - first_date).days + 1
        else:
            activity_days = 1
        
        return PlayerProfile(
            account_name=row['account_name'],
            character_names=row['character_names'].split(',') if row['character_names'] else [],
            professions_played=row['professions'].split(',') if row['professions'] else [],
            is_guild_member=is_guild_member,
            guild_rank=guild_rank,
            total_sessions=row['total_sessions'],
            first_session=row['first_session'] or '',
            last_session=row['last_session'] or '',
            activity_days=activity_days
        )
    
    def get_metric_summary(self, account_name: str, metric_name: str) -> Optional[MetricSummary]:
        """Get detailed summary for a specific metric."""
        if metric_name not in METRIC_CATEGORIES:
            return None
        
        cursor = self.conn.cursor()
        db_column = METRIC_CATEGORIES[metric_name]
        
        # Get Glicko rating data
        cursor.execute("""
            SELECT rating, rd, games_played, average_stat_value
            FROM glicko_ratings 
            WHERE account_name = ? AND metric_category = ?
        """, (account_name, metric_name))
        
        glicko_row = cursor.fetchone()
        if not glicko_row:
            return None
        
        # Get performance statistics
        cursor.execute(f"""
            SELECT 
                AVG({db_column}) as avg_value,
                MAX({db_column}) as best_value,
                MIN({db_column}) as worst_value
            FROM player_performances 
            WHERE account_name = ? AND {db_column} > 0 {self.date_clause}
        """, (account_name,) + tuple(self.date_params))
        
        stats_row = cursor.fetchone()
        
        # Calculate percentile rank
        cursor.execute(f"""
            SELECT COUNT(*) as total_players
            FROM (
                SELECT account_name, AVG({db_column}) as avg_metric
                FROM player_performances 
                WHERE {db_column} > 0 {self.date_clause}
                GROUP BY account_name
            )
        """, tuple(self.date_params))
        
        total_players = cursor.fetchone()['total_players']
        
        cursor.execute(f"""
            SELECT COUNT(*) as better_players
            FROM (
                SELECT account_name, AVG({db_column}) as avg_metric
                FROM player_performances 
                WHERE {db_column} > 0 {self.date_clause}
                GROUP BY account_name
                HAVING avg_metric > ?
            )
        """, tuple(self.date_params) + (stats_row['avg_value'],))
        
        better_players = cursor.fetchone()['better_players']
        percentile_rank = ((total_players - better_players) / total_players) * 100
        overall_rank = better_players + 1
        
        return MetricSummary(
            metric_name=metric_name,
            glicko_rating=glicko_row['rating'],
            rating_deviation=glicko_row['rd'],
            games_played=glicko_row['games_played'],
            average_value=stats_row['avg_value'] or 0,
            best_value=stats_row['best_value'] or 0,
            worst_value=stats_row['worst_value'] or 0,
            percentile_rank=percentile_rank,
            overall_rank=overall_rank,
            total_players=total_players
        )
    
    def get_profession_metric_summary(self, account_name: str, profession: str, metric_name: str) -> Optional[MetricSummary]:
        """Get detailed summary for a specific metric within a specific profession."""
        if metric_name not in METRIC_CATEGORIES:
            return None
        
        cursor = self.conn.cursor()
        db_column = METRIC_CATEGORIES[metric_name]
        
        # Get Glicko rating data for this profession
        cursor.execute("""
            SELECT rating, rd, games_played, average_stat_value
            FROM glicko_ratings 
            WHERE account_name = ? AND profession = ? AND metric_category = ?
        """, (account_name, profession, metric_name))
        
        glicko_row = cursor.fetchone()
        if not glicko_row:
            return None
        
        # Get performance statistics for this profession
        cursor.execute(f"""
            SELECT 
                AVG({db_column}) as avg_value,
                MAX({db_column}) as best_value,
                MIN({db_column}) as worst_value
            FROM player_performances 
            WHERE account_name = ? AND profession = ? AND {db_column} > 0 {self.date_clause}
        """, (account_name, profession) + tuple(self.date_params))
        
        stats_row = cursor.fetchone()
        
        # Check if we have valid stats
        if not stats_row or stats_row['avg_value'] is None:
            return None
        
        # Calculate percentile rank within this profession
        cursor.execute(f"""
            SELECT COUNT(*) as total_players
            FROM (
                SELECT account_name, AVG({db_column}) as avg_metric
                FROM player_performances 
                WHERE profession = ? AND {db_column} > 0 {self.date_clause}
                GROUP BY account_name
            )
        """, (profession,) + tuple(self.date_params))
        
        total_players = cursor.fetchone()['total_players']
        
        cursor.execute(f"""
            SELECT COUNT(*) as better_players
            FROM (
                SELECT account_name, AVG({db_column}) as avg_metric
                FROM player_performances 
                WHERE profession = ? AND {db_column} > 0 {self.date_clause}
                GROUP BY account_name
                HAVING avg_metric > ?
            )
        """, (profession,) + tuple(self.date_params) + (stats_row['avg_value'],))
        
        better_players = cursor.fetchone()['better_players']
        percentile_rank = ((total_players - better_players) / total_players) * 100 if total_players > 0 else 0
        overall_rank = better_players + 1
        
        return MetricSummary(
            metric_name=metric_name,
            glicko_rating=glicko_row['rating'],
            rating_deviation=glicko_row['rd'],
            games_played=glicko_row['games_played'],
            average_value=stats_row['avg_value'] or 0,
            best_value=stats_row['best_value'] or 0,
            worst_value=stats_row['worst_value'] or 0,
            percentile_rank=percentile_rank,
            overall_rank=overall_rank,
            total_players=total_players
        )
    
    def get_profession_summary(self, account_name: str, profession: str) -> Optional[ProfessionSummary]:
        """Get performance summary for a specific profession."""
        cursor = self.conn.cursor()
        
        # Get session count
        cursor.execute(f"""
            SELECT COUNT(DISTINCT timestamp) as sessions
            FROM player_performances 
            WHERE account_name = ? AND profession = ? {self.date_clause}
        """, (account_name, profession) + tuple(self.date_params))
        
        sessions = cursor.fetchone()['sessions']
        if sessions == 0:
            return None
        
        # Get profession-specific metrics if defined
        primary_metrics = {}
        if profession in PROFESSION_METRICS:
            prof_config = PROFESSION_METRICS[profession]
            for metric in prof_config['metrics']:
                if metric in METRIC_CATEGORIES:
                    db_column = METRIC_CATEGORIES[metric]
                    cursor.execute(f"""
                        SELECT AVG({db_column}) as avg_value
                        FROM player_performances 
                        WHERE account_name = ? AND profession = ? AND {db_column} > 0 {self.date_clause}
                    """, (account_name, profession) + tuple(self.date_params))
                    
                    result = cursor.fetchone()
                    if result and result['avg_value']:
                        primary_metrics[metric] = result['avg_value']
        
        # Get overall Glicko rating for this profession if it exists
        overall_glicko = 1500.0
        if profession in PROFESSION_METRICS:
            cursor.execute("""
                SELECT rating
                FROM glicko_ratings 
                WHERE account_name = ? AND profession = ? AND metric_category = 'Overall'
            """, (account_name, profession))
            
            rating_row = cursor.fetchone()
            if rating_row:
                overall_glicko = rating_row['rating']
        
        # Get best session
        cursor.execute(f"""
            SELECT timestamp, target_dps, all_damage
            FROM player_performances 
            WHERE account_name = ? AND profession = ? {self.date_clause}
            ORDER BY target_dps DESC
            LIMIT 1
        """, (account_name, profession) + tuple(self.date_params))
        
        best_session_row = cursor.fetchone()
        best_session = {
            'timestamp': best_session_row['timestamp'],
            'dps': best_session_row['target_dps'],
            'damage': best_session_row['all_damage']
        } if best_session_row else {}
        
        # Calculate trend (simplified)
        recent_trend = "stable"  # Placeholder for now
        
        # Get detailed metric summaries for this profession (use overall rankings)
        metric_summaries = []
        for metric_name in METRIC_CATEGORIES.keys():
            summary = self.get_metric_summary(account_name, metric_name)
            if summary:
                metric_summaries.append(summary)
        
        return ProfessionSummary(
            profession=profession,
            sessions_played=sessions,
            primary_metrics=primary_metrics,
            overall_glicko=overall_glicko,
            best_session=best_session,
            recent_trend=recent_trend,
            metric_summaries=metric_summaries
        )
    
    def get_recent_sessions(self, account_name: str, limit: int = 10) -> List[SessionSummary]:
        """Get recent session summaries."""
        cursor = self.conn.cursor()
        
        # Get recent sessions with context
        cursor.execute(f"""
            SELECT 
                pp.timestamp,
                pp.profession,
                pp.target_dps,
                pp.healing_per_sec,
                pp.barrier_per_sec,
                pp.stability_gen_per_sec
            FROM player_performances pp
            WHERE pp.account_name = ? {self.date_clause}
            ORDER BY pp.timestamp DESC
            LIMIT ?
        """, (account_name,) + tuple(self.date_params) + (limit,))
        
        sessions = []
        for row in cursor.fetchall():
            # Calculate session context (simplified)
            session_rank = 1  # Placeholder
            total_players = 20  # Placeholder
            
            key_stats = {
                'DPS': row['target_dps'],
                'Healing': row['healing_per_sec'],
                'Barrier': row['barrier_per_sec'],
                'Stability': row['stability_gen_per_sec']
            }
            
            # Simple performance grading
            performance_grade = "B"  # Placeholder
            
            sessions.append(SessionSummary(
                timestamp=row['timestamp'],
                profession=row['profession'],
                session_rank=session_rank,
                total_players=total_players,
                key_stats=key_stats,
                performance_grade=performance_grade
            ))
        
        return sessions
    
    def calculate_trends(self, account_name: str) -> Dict[str, Any]:
        """Calculate performance trends over time."""
        # Placeholder for trend analysis
        return {
            'overall_trend': 'improving',
            'best_metric': 'DPS',
            'improvement_rate': 5.2,
            'consistency_score': 0.75
        }
    
    def get_rankings(self, account_name: str) -> Dict[str, Any]:
        """Get player's current rankings."""
        cursor = self.conn.cursor()
        
        # Get overall DPS ranking
        cursor.execute(f"""
            SELECT COUNT(*) + 1 as rank
            FROM (
                SELECT account_name, AVG(target_dps) as avg_dps
                FROM player_performances 
                WHERE target_dps > 0 {self.date_clause}
                GROUP BY account_name
                HAVING avg_dps > (
                    SELECT AVG(target_dps)
                    FROM player_performances 
                    WHERE account_name = ? AND target_dps > 0 {self.date_clause}
                )
            )
        """, tuple(self.date_params) + (account_name,) + tuple(self.date_params))
        
        dps_rank = cursor.fetchone()['rank']
        
        return {
            'overall_dps_rank': dps_rank,
            'guild_rank': None,  # Placeholder
            'profession_ranks': {}  # Placeholder
        }
    
    def generate_summary(self, account_name: str, time_period: str = 'all') -> Optional[PlayerSummary]:
        """Generate complete player summary."""
        profile = self.get_player_profile(account_name)
        if not profile:
            return None
        
        # Get metric summaries
        metric_summaries = []
        for metric_name in METRIC_CATEGORIES.keys():
            summary = self.get_metric_summary(account_name, metric_name)
            if summary:
                metric_summaries.append(summary)
        
        # Get profession summaries
        profession_summaries = []
        for profession in profile.professions_played:
            summary = self.get_profession_summary(account_name, profession)
            if summary:
                profession_summaries.append(summary)
        
        # Get recent sessions
        recent_sessions = self.get_recent_sessions(account_name)
        
        # Calculate trends and rankings
        trends = self.calculate_trends(account_name)
        rankings = self.get_rankings(account_name)
        
        # Calculate overall stats
        overall_stats = {
            'activity_score': min(100, (profile.total_sessions / 10) * 100),
            'consistency_score': trends.get('consistency_score', 0.5) * 100,
            'improvement_rate': trends.get('improvement_rate', 0)
        }
        
        return PlayerSummary(
            profile=profile,
            overall_stats=overall_stats,
            metric_summaries=metric_summaries,
            profession_summaries=profession_summaries,
            recent_sessions=recent_sessions,
            trends=trends,
            rankings=rankings
        )


def format_console_output(summary: PlayerSummary) -> str:
    """Format player summary for console output."""
    output = []
    
    # Header
    output.append("=" * 80)
    output.append(f"PLAYER SUMMARY: {summary.profile.account_name}")
    output.append("=" * 80)
    
    # Profile section
    output.append("\n📋 PROFILE")
    output.append("-" * 40)
    output.append(f"Guild Member: {'Yes' if summary.profile.is_guild_member else 'No'}")
    if summary.profile.guild_rank:
        output.append(f"Guild Rank: {summary.profile.guild_rank}")
    output.append(f"Total Sessions: {summary.profile.total_sessions}")
    output.append(f"Activity Period: {summary.profile.activity_days} days")
    output.append(f"Professions: {', '.join(summary.profile.professions_played)}")
    
    # Overall stats
    output.append("\n📊 OVERALL PERFORMANCE")
    output.append("-" * 40)
    output.append(f"Activity Score: {summary.overall_stats['activity_score']:.1f}/100")
    output.append(f"Consistency Score: {summary.overall_stats['consistency_score']:.1f}/100")
    output.append(f"Overall DPS Rank: #{summary.rankings['overall_dps_rank']}")
    
    # Metric performance
    output.append("\n🎯 METRIC PERFORMANCE")
    output.append("-" * 80)
    output.append(f"{'Metric':<12} {'Glicko':<8} {'Games':<6} {'Avg Value':<10} {'Rank':<8} {'Percentile':<10}")
    output.append("-" * 80)
    
    for metric in summary.metric_summaries:
        output.append(f"{metric.metric_name:<12} {metric.glicko_rating:<8.0f} "
                     f"{metric.games_played:<6} {metric.average_value:<10.1f} "
                     f"#{metric.overall_rank:<7} {metric.percentile_rank:<10.1f}%")
    
    # Profession breakdown
    if summary.profession_summaries:
        output.append("\n⚔️ PROFESSION BREAKDOWN")
        output.append("-" * 60)
        
        for prof in summary.profession_summaries:
            output.append(f"\n{prof.profession} ({prof.sessions_played} sessions)")
            output.append(f"  Glicko Rating: {prof.overall_glicko:.0f}")
            
            if prof.primary_metrics:
                output.append("  Key Metrics:")
                for metric, value in prof.primary_metrics.items():
                    output.append(f"    {metric}: {value:.1f}")
    
    # Recent sessions
    if summary.recent_sessions:
        output.append("\n📅 RECENT SESSIONS")
        output.append("-" * 60)
        output.append(f"{'Date':<12} {'Profession':<15} {'Rank':<6} {'DPS':<8} {'Grade':<5}")
        output.append("-" * 60)
        
        for session in summary.recent_sessions[:5]:
            date_str = session.timestamp[:8]
            formatted_date = f"{date_str[4:6]}/{date_str[6:8]}/{date_str[2:4]}"
            output.append(f"{formatted_date:<12} {session.profession:<15} "
                         f"{session.session_rank:<6} {session.key_stats.get('DPS', 0):<8.0f} "
                         f"{session.performance_grade:<5}")
    
    output.append("\n" + "=" * 80)
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description='Generate comprehensive player summary')
    parser.add_argument('database', help='SQLite database file')
    parser.add_argument('account_name', help='Player account name to analyze')
    parser.add_argument('--format', choices=['console', 'json', 'html'], default='console',
                       help='Output format')
    parser.add_argument('--time-period', choices=['30d', '90d', '180d', 'all'], default='all',
                       help='Time period to analyze')
    parser.add_argument('--output', help='Output file (optional)')
    
    args = parser.parse_args()
    
    if not Path(args.database).exists():
        print(f"Database {args.database} not found")
        return 1
    
    generator = PlayerSummaryGenerator(args.database)
    
    try:
        summary = generator.generate_summary(args.account_name, args.time_period)
        
        if not summary:
            print(f"No data found for player: {args.account_name}")
            return 1
        
        if args.format == 'console':
            output = format_console_output(summary)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"Console output saved to {args.output}")
            else:
                print(output)
        
        elif args.format == 'json':
            # Convert dataclasses to dict for JSON serialization
            def to_dict(obj):
                if hasattr(obj, '__dict__'):
                    return {k: to_dict(v) for k, v in obj.__dict__.items()}
                elif isinstance(obj, list):
                    return [to_dict(item) for item in obj]
                elif isinstance(obj, dict):
                    return {k: to_dict(v) for k, v in obj.items()}
                else:
                    return obj
            
            json_data = to_dict(summary)
            
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2)
                print(f"JSON output saved to {args.output}")
            else:
                print(json.dumps(json_data, indent=2))
        
        elif args.format == 'html':
            print("HTML format not yet implemented")
            return 1
    
    finally:
        generator.close()
    
    return 0


if __name__ == '__main__':
    exit(main())