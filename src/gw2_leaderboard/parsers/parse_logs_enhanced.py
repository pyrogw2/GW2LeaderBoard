#!/usr/bin/env python3
"""
Enhanced parser for GW2 log summaries to extract comprehensive player performance data.
Extracts 8 performance metrics: DPS, Healing/sec, Barrier/sec, Cleanses/sec, Strips/sec, Stability/sec, Resistance/sec, Might/sec
"""

import json
import re
import sqlite3
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import argparse
from datetime import datetime, date
from .high_scores_parser import HighScoresParser


@dataclass
class PlayerPerformance:
    timestamp: str
    player_name: str
    account_name: str
    profession: str
    party: int
    fight_time: float
    # DPS Metrics
    target_damage: int
    target_dps: int
    all_damage: int
    # Condition Damage Metrics
    target_condition_damage: int = 0
    target_condition_dps: int = 0
    # Support Metrics
    healing_per_sec: float = 0.0
    barrier_per_sec: float = 0.0
    condition_cleanses_per_sec: float = 0.0
    boon_strips_per_sec: float = 0.0
    # Boon Generation Metrics (per second)
    stability_gen_per_sec: float = 0.0
    resistance_gen_per_sec: float = 0.0
    might_gen_per_sec: float = 0.0
    protection_gen_per_sec: float = 0.0
    # Downstate Metrics (per second)
    down_contribution_per_sec: float = 0.0
    # Burst Metrics
    burst_damage_1s: int = 0  # Bur-Total (1)s - for High Scores section
    burst_consistency_1s: int = 0  # Ch5Ca-Total (1)s - for Glicko rating
    # Date fields
    parsed_date: date = None


def parse_timestamp_to_date(timestamp: str) -> date:
    """Parse timestamp string (YYYYMMDDHHMM) to date object."""
    try:
        # Extract year, month, day from timestamp
        year = int(timestamp[:4])
        month = int(timestamp[4:6])
        day = int(timestamp[6:8])
        return date(year, month, day)
    except (ValueError, IndexError):
        print(f"Warning: Could not parse timestamp {timestamp}")
        return None


def extract_tooltip(text: str) -> str:
    """Extract account name from tooltip attribute."""
    # Try both single and double quotes
    match = re.search(r'data-tooltip=["\']([^"\']+)["\']', text)
    return match.group(1) if match else ""


def extract_span_value(text: str) -> float:
    """Extract numeric value from HTML span tags, handling tooltips."""
    # Handle cases like: <span data-tooltip="X.XX Wasted">Y.Y</span>
    span_match = re.search(r'<span[^>]*>([0-9,]+\.?[0-9]*)</span>', text)
    if span_match:
        return float(span_match.group(1).replace(',', ''))
    
    # Handle direct numeric values
    direct_match = re.search(r'([0-9,]+\.?[0-9]*)', text.strip())
    if direct_match and text.strip() != '-':
        return float(direct_match.group(1).replace(',', ''))
    
    return 0.0


def parse_damage_table(damage_text: str) -> List[Dict]:
    """Parse the damage table from TiddlyWiki markup."""
    players = []
    
    lines = damage_text.split('\n')
    data_rows = [line for line in lines if line.startswith('|') and not line.startswith('|!') and not line.startswith('|thead')]
    
    for row in data_rows:
        if '|h' in row or not row.strip():
            continue
            
        cells = [cell.strip() for cell in row.split('|') if cell.strip()]
        
        if len(cells) < 14:
            continue
            
        try:
            party = int(cells[0]) if cells[0].isdigit() else 0
            
            # Parse player name and account
            name_cell = cells[1]
            account_name = extract_tooltip(name_cell)
            display_match = re.search(r'>([^<]+)</span>', name_cell)
            player_name = display_match.group(1) if display_match else ""
            
            # Parse profession
            prof_cell = cells[2]
            prof_match = re.search(r'{{(\w+)}}', prof_cell)
            profession = prof_match.group(1) if prof_match else ""
            
            # Parse numeric values
            fight_time = float(cells[3].replace(',', '')) if cells[3].replace(',', '').replace('.', '').isdigit() else 0
            target_damage = int(cells[4].replace(',', '')) if cells[4].replace(',', '').isdigit() else 0
            target_dps = int(cells[5].replace(',', '')) if cells[5].replace(',', '').isdigit() else 0
            # Condition damage columns (Target_Condition and Target_Condition_PS)
            target_condition_damage = int(cells[8].replace(',', '')) if len(cells) > 8 and cells[8].replace(',', '').isdigit() else 0
            target_condition_dps = int(cells[9].replace(',', '')) if len(cells) > 9 and cells[9].replace(',', '').isdigit() else 0
            all_damage = int(cells[11].replace(',', '')) if cells[11].replace(',', '').isdigit() else 0
            players.append({
                'party': party,
                'player_name': player_name,
                'account_name': account_name,
                'profession': profession,
                'fight_time': fight_time,
                'target_damage': target_damage,
                'target_dps': target_dps,
                'target_condition_damage': target_condition_damage,
                'target_condition_dps': target_condition_dps,
                'all_damage': all_damage
            })
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing damage row: {row[:100]}... - {e}")
            continue
    
    return players


def parse_offensive_table(offensive_text: str) -> Dict[str, Dict]:
    """Parse downContribution data from the offensive table."""
    offensive_stats = {}
    
    # Extract only the first section (Total section)
    total_section_start = offensive_text.find('text="Total"')
    total_section_end = offensive_text.find('</$reveal>', total_section_start)
    
    if total_section_start == -1 or total_section_end == -1:
        print(f"Warning: Could not find Total section in offensive table for {timestamp}")
        return offensive_stats
        
    total_section = offensive_text[total_section_start:total_section_end]
    
    lines = total_section.split('\n')
    data_rows = [line for line in lines if line.startswith('|') and not line.startswith('|!') and not line.startswith('|thead')]
    
    
    for row in data_rows:
        if '|h' in row or not row.strip() or '<$radio' in row:
            continue
            
        cells = [cell.strip() for cell in row.split('|') if cell.strip()]
        
        if len(cells) < 22:  # Need at least 22 columns for downContribution
            continue
            
        try:
            # Parse player name and account
            name_cell = cells[1]
            account_name = extract_tooltip(name_cell)
            if not account_name:
                continue
                
            # Parse profession
            prof_cell = cells[2]
            prof_match = re.search(r'{{(\w+)}}', prof_cell)
            profession = prof_match.group(1) if prof_match else ""
            
            
            # Extract downContribution from column 21 (0-based indexing)
            down_contribution = int(cells[21].replace(',', '')) if len(cells) > 21 and cells[21].replace(',', '').isdigit() else 0
            
            
            key = f"{account_name}_{profession}"
            offensive_stats[key] = {
                'account_name': account_name,
                'profession': profession,
                'down_contribution': down_contribution
            }
            
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing offensive row: {row[:100]}... - {e}")
            continue
    
    return offensive_stats


def parse_heal_table(heal_text: str) -> Dict[str, Dict]:
    """Parse healing and barrier stats from heal table (Squad section only)."""
    heal_stats = {}
    
    # Find the Squad section specifically
    squad_section_start = heal_text.find('stateField="category_heal" type="match" text="Squad"')
    if squad_section_start == -1:
        return heal_stats
    
    # Find the end of the Squad section
    squad_section_end = heal_text.find('</$reveal>', squad_section_start)
    if squad_section_end == -1:
        squad_section_end = len(heal_text)
    
    squad_text = heal_text[squad_section_start:squad_section_end]
    
    lines = squad_text.split('\n')
    data_rows = [line for line in lines if line.startswith('|') and not line.startswith('|!') and not line.startswith('|thead')]
    
    for row in data_rows:
        if '|h' in row or not row.strip() or 'Total' in row or 'Squad' in row or '</$radio>' in row:
            continue
            
        cells = [cell.strip() for cell in row.split('|') if cell.strip()]
        
        if len(cells) < 7:
            continue
            
        try:
            # Parse player name and account
            name_cell = cells[1]
            account_name = extract_tooltip(name_cell)
            if not account_name:
                continue
                
            # Parse profession
            prof_cell = cells[2]
            prof_match = re.search(r'{{(\w+)}}', prof_cell)
            profession = prof_match.group(1) if prof_match else ""
            
            # Parse healing and barrier per second
            healing_ps = extract_span_value(cells[5]) if len(cells) > 5 else 0.0
            barrier_ps = extract_span_value(cells[7]) if len(cells) > 7 else 0.0
            
            key = f"{account_name}_{profession}"
            heal_stats[key] = {
                'account_name': account_name,
                'profession': profession,
                'healing_per_sec': healing_ps,
                'barrier_per_sec': barrier_ps
            }
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing heal row: {row[:100]}... - {e}")
            continue
    
    return heal_stats


def parse_support_table(support_text: str) -> Dict[str, Dict]:
    """Parse condition cleanses and boon strips from support table."""
    support_stats = {}
    
    # Look for the "Stat/1s" section which has per-second values
    lines = support_text.split('\n')
    in_stats_section = False
    
    for line in lines:
        if 'Stat/1s' in line and 'animate="yes"' in line:
            in_stats_section = True
            continue
        elif 'animate="yes"' in line and in_stats_section:
            break
        elif not in_stats_section:
            continue
            
        if not line.startswith('|') or line.startswith('|!') or line.startswith('|thead'):
            continue
            
        if '|h' in line or not line.strip():
            continue
            
        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
        
        if len(cells) < 10:
            continue
            
        try:
            # Parse player name and account
            name_cell = cells[1]
            account_name = extract_tooltip(name_cell)
            if not account_name:
                continue
                
            # Parse profession
            prof_cell = cells[2]
            prof_match = re.search(r'{{(\w+)}}', prof_cell)
            profession = prof_match.group(1) if prof_match else ""
            
            # Parse cleanses and strips per second (already per-second in this table)
            cleanses_ps = extract_span_value(cells[4]) if len(cells) > 4 else 0.0
            strips_ps = extract_span_value(cells[8]) if len(cells) > 8 else 0.0
            
            key = f"{account_name}_{profession}"
            support_stats[key] = {
                'account_name': account_name,
                'profession': profession,
                'condition_cleanses_per_sec': cleanses_ps,
                'boon_strips_per_sec': strips_ps
            }
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing support row: {line[:100]}... - {e}")
            continue
    
    return support_stats


def parse_boon_generation_table(boon_text: str) -> Dict[str, Dict]:
    """Parse boon generation stats (Stability, Resistance, Might) from squad generation table."""
    boon_stats = {}
    
    # Look for the "Average" section which has per-second values
    lines = boon_text.split('\n')
    in_average_section = False
    
    for line in lines:
        if '"Average"' in line and 'animate="yes"' in line:
            in_average_section = True
            continue
        elif 'animate="yes"' in line and in_average_section:
            break
        elif not in_average_section:
            continue
            
        if not line.startswith('|') or line.startswith('|!') or line.startswith('|thead'):
            continue
            
        if '|h' in line or not line.strip():
            continue
            
        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
        
        if len(cells) < 15:  # Need enough columns for boon data
            continue
            
        try:
            # Parse player name and account
            name_cell = cells[1]
            account_name = extract_tooltip(name_cell)
            if not account_name:
                continue
                
            # Parse profession
            prof_cell = cells[2]
            prof_match = re.search(r'{{(\w+)}}', prof_cell)
            profession = prof_match.group(1) if prof_match else ""
            
            # Find boon columns based on header pattern
            # Standard order: Might, Fury, Quickness, Alacrity, Protection, Regeneration, Vigor, Aegis, Stability, Swiftness, Resistance, Resolution, Superspeed, Stealth
            might_ps = extract_span_value(cells[4]) if len(cells) > 4 else 0.0  # Might column
            protection_ps = extract_span_value(cells[8]) if len(cells) > 8 else 0.0  # Protection column
            stability_ps = extract_span_value(cells[12]) if len(cells) > 12 else 0.0  # Stability column
            resistance_ps = extract_span_value(cells[14]) if len(cells) > 14 else 0.0  # Resistance column
            
            key = f"{account_name}_{profession}"
            boon_stats[key] = {
                'account_name': account_name,
                'profession': profession,
                'stability_gen_per_sec': stability_ps,
                'resistance_gen_per_sec': resistance_ps,
                'might_gen_per_sec': might_ps,
                'protection_gen_per_sec': protection_ps
            }
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing boon row: {line[:100]}... - {e}")
            continue
    
    return boon_stats


def parse_burst_damage_table(burst_text: str) -> Dict[str, Dict]:
    """Parse Bur-Total (1)s data for highest 1-second burst damage."""
    burst_stats = {}
    
    lines = burst_text.split('\n')
    data_rows = [line for line in lines if line.startswith('|') and not line.startswith('|!') and not line.startswith('|thead')]
    
    for row in data_rows:
        if '|h' in row or not row.strip() or '|!' in row or '|c' in row:
            continue
            
        try:
            cells = [cell.strip() for cell in row.split('|')[1:-1]]  # Remove empty first/last
            if len(cells) < 6:
                continue
            
            # Extract account name from tooltip
            name_cell = cells[0]
            account_name = extract_tooltip(name_cell)
            if not account_name:
                continue
                
            # Parse profession
            prof_cell = cells[1]
            prof_match = re.search(r'{{(\w+)}}', prof_cell)
            profession = prof_match.group(1) if prof_match else ""
            
            # Extract Bur-Total (1)s value - should be column 5 (0-indexed)
            burst_1s_cell = cells[5] if len(cells) > 5 else ""
            burst_1s = extract_span_value(burst_1s_cell) if burst_1s_cell else 0
            
            key = f"{account_name}_{profession}"
            burst_stats[key] = {
                'account_name': account_name,
                'profession': profession,
                'burst_damage_1s': int(burst_1s)
            }
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing burst damage row: {row[:100]}... - {e}")
            continue
    
    return burst_stats


def parse_burst_consistency_table(consistency_text: str) -> Dict[str, Dict]:
    """Parse Ch5Ca-Total (1)s data for burst consistency (Glicko rating)."""
    consistency_stats = {}
    
    lines = consistency_text.split('\n')
    data_rows = [line for line in lines if line.startswith('|') and not line.startswith('|!') and not line.startswith('|thead')]
    
    for row in data_rows:
        if '|h' in row or not row.strip() or '|!' in row or '|c' in row:
            continue
            
        try:
            cells = [cell.strip() for cell in row.split('|')[1:-1]]  # Remove empty first/last
            if len(cells) < 6:
                continue
            
            # Extract account name from tooltip
            name_cell = cells[0]
            account_name = extract_tooltip(name_cell)
            if not account_name:
                continue
                
            # Parse profession
            prof_cell = cells[1]
            prof_match = re.search(r'{{(\w+)}}', prof_cell)
            profession = prof_match.group(1) if prof_match else ""
            
            # Extract Ch5Ca-Total (1)s value - should be column 5 (0-indexed)
            consistency_1s_cell = cells[5] if len(cells) > 5 else ""
            consistency_1s = extract_span_value(consistency_1s_cell) if consistency_1s_cell else 0
            
            key = f"{account_name}_{profession}"
            consistency_stats[key] = {
                'account_name': account_name,
                'profession': profession,
                'burst_consistency_1s': int(consistency_1s)
            }
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing burst consistency row: {row[:100]}... - {e}")
            continue
    
    return consistency_stats


def parse_log_directory(log_dir: Path) -> List[PlayerPerformance]:
    """Parse a single log directory and extract comprehensive player performance data."""
    timestamp = log_dir.name
    
    # Read damage data (base data)
    damage_file = log_dir / f"{timestamp}-Damage.json"
    if not damage_file.exists():
        print(f"No damage file found for {timestamp}")
        return []
    
    with open(damage_file, 'r', encoding='utf-8') as f:
        damage_data = json.load(f)
    
    damage_text = damage_data.get('text', '')
    players_data = parse_damage_table(damage_text)
    
    # Read offensive data for downContribution
    offensive_stats = {}
    offensive_file = log_dir / f"{timestamp}-Offensive.json"
    if offensive_file.exists():
        with open(offensive_file, 'r', encoding='utf-8') as f:
            offensive_data = json.load(f)
        offensive_stats = parse_offensive_table(offensive_data.get('text', ''))
    
    # Read healing data
    heal_stats = {}
    heal_file = log_dir / f"{timestamp}-Heal-Stats.json"
    if heal_file.exists():
        with open(heal_file, 'r', encoding='utf-8') as f:
            heal_data = json.load(f)
        heal_stats = parse_heal_table(heal_data.get('text', ''))
    
    # Read support data
    support_stats = {}
    support_file = log_dir / f"{timestamp}-Support.json"
    if support_file.exists():
        with open(support_file, 'r', encoding='utf-8') as f:
            support_data = json.load(f)
        support_stats = parse_support_table(support_data.get('text', ''))
    
    # Read boon generation data
    boon_stats = {}
    boon_file = log_dir / f"{timestamp}-Squad-Generation.json"
    if boon_file.exists():
        with open(boon_file, 'r', encoding='utf-8') as f:
            boon_data = json.load(f)
        boon_stats = parse_boon_generation_table(boon_data.get('text', ''))
    
    # Read burst damage data (Bur-Total)
    burst_damage_stats = {}
    burst_damage_file = log_dir / f"{timestamp}-DPS-Stats-Bur-Total.json"
    if burst_damage_file.exists():
        with open(burst_damage_file, 'r', encoding='utf-8') as f:
            burst_damage_data = json.load(f)
        burst_damage_stats = parse_burst_damage_table(burst_damage_data.get('text', ''))
    
    # Read burst consistency data (Ch5Ca-Total)
    burst_consistency_stats = {}
    burst_consistency_file = log_dir / f"{timestamp}-DPS-Stats-Ch5Ca-Total.json"
    if burst_consistency_file.exists():
        with open(burst_consistency_file, 'r', encoding='utf-8') as f:
            burst_consistency_data = json.load(f)
        burst_consistency_stats = parse_burst_consistency_table(burst_consistency_data.get('text', ''))
    
    # Combine all stats into PlayerPerformance objects
    performances = []
    for player_data in players_data:
        if not player_data['player_name'] or not player_data['account_name']:
            continue
        
        account = player_data['account_name']
        profession = player_data['profession']
        key = f"{account}_{profession}"
        
        # Get additional stats
        heal_data = heal_stats.get(key, {})
        support_data = support_stats.get(key, {})
        boon_data = boon_stats.get(key, {})
        offensive_data = offensive_stats.get(key, {})
        burst_damage_data = burst_damage_stats.get(key, {})
        burst_consistency_data = burst_consistency_stats.get(key, {})
        
        
        performance = PlayerPerformance(
            timestamp=timestamp,
            parsed_date=parse_timestamp_to_date(timestamp),
            player_name=player_data['player_name'],
            account_name=account,
            profession=profession,
            party=player_data['party'],
            fight_time=player_data['fight_time'],
            target_damage=player_data['target_damage'],
            target_dps=player_data['target_dps'],
            all_damage=player_data['all_damage'],
            target_condition_damage=player_data.get('target_condition_damage', 0),
            target_condition_dps=player_data.get('target_condition_dps', 0),
            healing_per_sec=heal_data.get('healing_per_sec', 0.0),
            barrier_per_sec=heal_data.get('barrier_per_sec', 0.0),
            condition_cleanses_per_sec=support_data.get('condition_cleanses_per_sec', 0.0),
            boon_strips_per_sec=support_data.get('boon_strips_per_sec', 0.0),
            stability_gen_per_sec=boon_data.get('stability_gen_per_sec', 0.0),
            resistance_gen_per_sec=boon_data.get('resistance_gen_per_sec', 0.0),
            might_gen_per_sec=boon_data.get('might_gen_per_sec', 0.0),
            protection_gen_per_sec=boon_data.get('protection_gen_per_sec', 0.0),
            down_contribution_per_sec=offensive_data.get('down_contribution', 0) / player_data['fight_time'] if player_data['fight_time'] > 0 else 0.0,
            burst_damage_1s=burst_damage_data.get('burst_damage_1s', 0),
            burst_consistency_1s=burst_consistency_data.get('burst_consistency_1s', 0)
        )
        performances.append(performance)
    
    # Apply build detection to classify variants
    performances = detect_build_variants(performances)
    
    return performances


def detect_build_variants(performances: List[PlayerPerformance]) -> List[PlayerPerformance]:
    """Detect and reclassify build variants based on performance patterns."""
    if not performances:
        return performances
    
    # Calculate session-wide stats for build detection
    all_condition_dps = [p.target_condition_dps for p in performances if p.target_condition_dps > 0]
    all_resistance_gen = [p.resistance_gen_per_sec for p in performances if p.resistance_gen_per_sec > 0]
    all_stability_gen = [p.stability_gen_per_sec for p in performances if p.stability_gen_per_sec > 0]
    
    import statistics
    
    # Detect Condi Firebrand: Firebrand with condition DPS significantly above average
    condi_fb_threshold = 200  # Default minimum threshold
    if len(all_condition_dps) >= 2:
        mean_condition_dps = statistics.mean(all_condition_dps)
        condi_fb_threshold = max(mean_condition_dps * 1.5, 200)
    
    # Detect Support Spellbreaker: Spellbreaker with resistance generation significantly above average
    support_sb_threshold = 0.5  # Default minimum threshold (resistance/sec)
    if len(all_resistance_gen) >= 2:
        mean_resistance_gen = statistics.mean(all_resistance_gen)
        support_sb_threshold = max(mean_resistance_gen * 1.2, 0.5)
    
    # Detect China DH: Dragonhunter with stability generation significantly above average
    china_dh_threshold = 3.0  # Default minimum threshold (stability/sec)
    if len(all_stability_gen) >= 2:
        mean_stability_gen = statistics.mean(all_stability_gen)
        china_dh_threshold = max(mean_stability_gen * 1.2, 3.0)
    
    # Detect Boon Vindi: Vindicator with protection generation significantly above average
    all_protection_gen = [p.protection_gen_per_sec for p in performances if p.protection_gen_per_sec > 0]
    boon_vindi_threshold = 1.0  # Default minimum threshold (protection/sec)
    if len(all_protection_gen) >= 2:
        mean_protection_gen = statistics.mean(all_protection_gen)
        boon_vindi_threshold = max(mean_protection_gen * 1.2, 1.0)
    
    updated_performances = []
    for performance in performances:
        new_profession = performance.profession  # Default to original
        
        # Check for Condi Firebrand
        if (performance.profession == "Firebrand" and 
            performance.target_condition_dps >= condi_fb_threshold):
            new_profession = "Condi Firebrand"
        
        # Check for Support Spellbreaker
        elif (performance.profession == "Spellbreaker" and 
              performance.resistance_gen_per_sec >= support_sb_threshold):
            new_profession = "Support Spb"
        
        # Check for China DH
        elif (performance.profession == "Dragonhunter" and 
              performance.stability_gen_per_sec >= china_dh_threshold):
            new_profession = "China DH"
        
        # Check for Boon Vindi
        elif (performance.profession == "Vindicator" and 
              performance.protection_gen_per_sec >= boon_vindi_threshold):
            new_profession = "Boon Vindi"
        
        # Create performance object with potentially updated profession
        updated_performance = PlayerPerformance(
            timestamp=performance.timestamp,
            parsed_date=performance.parsed_date,  # Preserve parsed date
            player_name=performance.player_name,
            account_name=performance.account_name,
            profession=new_profession,  # Use detected profession
            party=performance.party,
            fight_time=performance.fight_time,
            target_damage=performance.target_damage,
            target_dps=performance.target_dps,
            all_damage=performance.all_damage,
            target_condition_damage=performance.target_condition_damage,
            target_condition_dps=performance.target_condition_dps,
            healing_per_sec=performance.healing_per_sec,
            barrier_per_sec=performance.barrier_per_sec,
            condition_cleanses_per_sec=performance.condition_cleanses_per_sec,
            boon_strips_per_sec=performance.boon_strips_per_sec,
            stability_gen_per_sec=performance.stability_gen_per_sec,
            resistance_gen_per_sec=performance.resistance_gen_per_sec,
            might_gen_per_sec=performance.might_gen_per_sec,
            protection_gen_per_sec=performance.protection_gen_per_sec,
            down_contribution_per_sec=performance.down_contribution_per_sec,
            burst_damage_1s=performance.burst_damage_1s,
            burst_consistency_1s=performance.burst_consistency_1s
        )
        updated_performances.append(updated_performance)
    
    return updated_performances


def create_database(db_path: str):
    """Create SQLite database with comprehensive player performance schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop existing table to recreate with new schema
    cursor.execute('DROP TABLE IF EXISTS player_performances')
    
    cursor.execute('''
        CREATE TABLE player_performances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            parsed_date TEXT,
            player_name TEXT NOT NULL,
            account_name TEXT NOT NULL,
            profession TEXT NOT NULL,
            party INTEGER,
            fight_time REAL,
            target_damage INTEGER,
            target_dps INTEGER,
            all_damage INTEGER,
            target_condition_damage INTEGER DEFAULT 0,
            target_condition_dps INTEGER DEFAULT 0,
            healing_per_sec REAL DEFAULT 0.0,
            barrier_per_sec REAL DEFAULT 0.0,
            condition_cleanses_per_sec REAL DEFAULT 0.0,
            boon_strips_per_sec REAL DEFAULT 0.0,
            stability_gen_per_sec REAL DEFAULT 0.0,
            resistance_gen_per_sec REAL DEFAULT 0.0,
            might_gen_per_sec REAL DEFAULT 0.0,
            protection_gen_per_sec REAL DEFAULT 0.0,
            down_contribution_per_sec REAL DEFAULT 0.0,
            burst_damage_1s INTEGER DEFAULT 0,
            burst_consistency_1s INTEGER DEFAULT 0,
            UNIQUE(timestamp, account_name, profession)
        )
    ''')
    
    # Create rating tables for each metric category
    cursor.execute('DROP TABLE IF EXISTS player_ratings')
    cursor.execute('''
        CREATE TABLE player_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT NOT NULL,
            profession TEXT NOT NULL,
            metric_category TEXT NOT NULL,
            elo_rating REAL DEFAULT 1200,
            games_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            UNIQUE(account_name, profession, metric_category)
        )
    ''')
    
    # Create high scores table
    cursor.execute('DROP TABLE IF EXISTS high_scores')
    cursor.execute('''
        CREATE TABLE high_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            parsed_date TEXT,
            player_account TEXT NOT NULL,
            player_name TEXT NOT NULL,
            profession TEXT NOT NULL,
            fight_number INTEGER NOT NULL,
            metric_type TEXT NOT NULL,
            skill_name TEXT,
            skill_icon_url TEXT,
            score_value REAL NOT NULL
        )
    ''')
    
    # Create indexes for efficient querying
    cursor.execute('CREATE INDEX idx_high_scores_metric ON high_scores(metric_type)')
    cursor.execute('CREATE INDEX idx_high_scores_date ON high_scores(parsed_date)')
    cursor.execute('CREATE INDEX idx_high_scores_player ON high_scores(player_account)')
    cursor.execute('CREATE INDEX idx_high_scores_score ON high_scores(metric_type, score_value DESC)')
    
    conn.commit()
    conn.close()


def store_high_scores(high_scores: List, db_path: str):
    """Store high scores data in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for entry in high_scores:
        cursor.execute('''
            INSERT OR REPLACE INTO high_scores (
                timestamp, parsed_date, player_account, player_name, profession,
                fight_number, metric_type, skill_name, skill_icon_url, score_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.timestamp,
            str(entry.timestamp[:8]),  # Convert YYYYMMDDHHMM to YYYYMMDD
            entry.player_account,
            entry.player_name,
            entry.profession,
            entry.fight_number,
            entry.metric_type,
            entry.skill_name,
            entry.skill_icon_url,
            entry.score_value
        ))
    
    conn.commit()
    conn.close()
    print(f"Stored {len(high_scores)} high score entries")


def store_performances(performances: List[PlayerPerformance], db_path: str):
    """Store comprehensive player performances in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for perf in performances:
        cursor.execute('''
            INSERT OR REPLACE INTO player_performances 
            (timestamp, parsed_date, player_name, account_name, profession, party, fight_time,
             target_damage, target_dps, all_damage, target_condition_damage, target_condition_dps,
             healing_per_sec, barrier_per_sec, condition_cleanses_per_sec, boon_strips_per_sec, 
             stability_gen_per_sec, resistance_gen_per_sec, might_gen_per_sec, protection_gen_per_sec, down_contribution_per_sec,
             burst_damage_1s, burst_consistency_1s)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            perf.timestamp, perf.parsed_date.isoformat() if perf.parsed_date else None,
            perf.player_name, perf.account_name, perf.profession,
            perf.party, perf.fight_time, perf.target_damage, perf.target_dps,
            perf.all_damage, perf.target_condition_damage, perf.target_condition_dps,
            perf.healing_per_sec, perf.barrier_per_sec, perf.condition_cleanses_per_sec, 
            perf.boon_strips_per_sec, perf.stability_gen_per_sec, perf.resistance_gen_per_sec, 
            perf.might_gen_per_sec, perf.protection_gen_per_sec, perf.down_contribution_per_sec,
            perf.burst_damage_1s, perf.burst_consistency_1s
        ))
    
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Parse GW2 log summaries with comprehensive metrics')
    parser.add_argument('logs_dir', help='Directory containing extracted log folders')
    parser.add_argument('-d', '--database', default='gw2_leaderboard_comprehensive.db',
                        help='SQLite database file (default: gw2_leaderboard_comprehensive.db)')
    
    args = parser.parse_args()
    
    logs_path = Path(args.logs_dir)
    if not logs_path.exists():
        print(f"Directory {logs_path} does not exist")
        return 1
    
    # Create database
    create_database(args.database)
    print(f"Created comprehensive database: {args.database}")
    
    # Process each log directory
    all_performances = []
    all_high_scores = []
    
    # Initialize high scores parser
    high_scores_parser = HighScoresParser()
    
    for log_dir in sorted(logs_path.iterdir()):
        if log_dir.is_dir() and re.match(r'\d{12}', log_dir.name):
            print(f"Processing {log_dir.name}...")
            performances = parse_log_directory(log_dir)
            all_performances.extend(performances)
            print(f"  Found {len(performances)} player performances")
            
            # Process high scores for this log directory
            high_scores_file = log_dir / f"{log_dir.name}-High-Scores.json"
            if high_scores_file.exists():
                high_scores = high_scores_parser.parse_high_scores_file(high_scores_file)
                all_high_scores.extend(high_scores)
                print(f"  Found {len(high_scores)} high score entries")
            else:
                print(f"  No High-Scores.json found")
    
    # Store in database
    if all_performances:
        store_performances(all_performances, args.database)
        print(f"Stored {len(all_performances)} comprehensive performances in database")
    
    if all_high_scores:
        store_high_scores(all_high_scores, args.database)
        print(f"Stored {len(all_high_scores)} high score entries in database")
        
        # Show summary
        conn = sqlite3.connect(args.database)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(DISTINCT account_name) FROM player_performances')
        unique_players = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT timestamp) FROM player_performances')
        unique_sessions = cursor.fetchone()[0]
        
        # Show metrics summary
        metrics = ['target_dps', 'healing_per_sec', 'barrier_per_sec', 'condition_cleanses_per_sec', 
                  'boon_strips_per_sec', 'stability_gen_per_sec', 'resistance_gen_per_sec', 'might_gen_per_sec']
        
        # Get high scores summary
        cursor.execute('SELECT COUNT(*) FROM high_scores')
        result = cursor.fetchone()
        total_high_scores = result[0] if result else 0
        
        cursor.execute('SELECT COUNT(DISTINCT metric_type) FROM high_scores')
        result = cursor.fetchone()
        unique_metrics = result[0] if result else 0
        
        print(f"\nSummary:")
        print(f"  Unique players: {unique_players}")
        print(f"  Gaming sessions: {unique_sessions}")
        print(f"  Metrics tracked: {len(metrics)}")
        print(f"  High score entries: {total_high_scores}")
        print(f"  High score metric types: {unique_metrics}")
        
        print(f"\nTop performers by metric:")
        for metric in metrics:
            cursor.execute(f'SELECT account_name, profession, MAX({metric}) FROM player_performances WHERE {metric} > 0')
            result = cursor.fetchone()
            if result and result[2]:
                print(f"  {metric}: {result[0]} ({result[1]}) - {result[2]:.1f}")
        
        conn.close()
    
    return 0


if __name__ == '__main__':
    exit(main())