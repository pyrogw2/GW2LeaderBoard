#!/usr/bin/env python3
"""
High Scores Parser for GW2 TiddlyWiki Log Data

This module parses High-Scores.json files from extracted_logs directories
and extracts structured data for:
- Highest Outgoing Skill Damage
- Highest Incoming Skill Damage  
- Damage per Second (as "Highest Single Fight DPS")

The parser handles TiddlyWiki table markup and extracts player information,
skill details, and performance scores.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HighScoreEntry:
    """Represents a single high score entry"""
    timestamp: str
    player_account: str
    player_name: str
    profession: str
    fight_number: int
    metric_type: str
    skill_name: Optional[str]
    skill_icon_url: Optional[str]
    score_value: float


class HighScoresParser:
    """Parser for High-Scores.json files from GW2 TiddlyWiki logs"""
    
    # Target metrics we want to extract
    TARGET_METRICS = {
        'Highest Outgoing Skill Damage': 'highest_outgoing_skill_damage',
        'Highest Incoming Skill Damage': 'highest_incoming_skill_damage',
        'Damage per Second': 'highest_single_fight_dps'
    }
    
    def __init__(self):
        # Regex patterns for parsing TiddlyWiki markup
        self.player_pattern = re.compile(
            r"<span data-tooltip='([^']+)'>\s*{{([^}]+)}}([^<]+)\s*</span>-(\d+)"
        )
        self.skill_pattern = re.compile(
            r"\[img width=24 \[([^|]+)\|([^]]+)\]\]-([^|]+)"
        )
        self.score_pattern = re.compile(r'[\d,]+\.?\d*')
        
    def extract_player_info(self, player_text: str) -> Optional[Tuple[str, str, str, int]]:
        """
        Extract player information from Player-Fight format.
        
        Args:
            player_text: Raw player text like "<span data-tooltip='synco.8132'> {{Catalyst}}Synco E </span>-21"
            
        Returns:
            Tuple of (account_name, profession, display_name, fight_number) or None
        """
        match = self.player_pattern.search(player_text)
        if match:
            account_name = match.group(1)
            profession = match.group(2)
            display_name = match.group(3).strip()
            fight_number = int(match.group(4))
            return account_name, profession, display_name, fight_number
        return None
    
    def extract_skill_info(self, skill_text: str) -> Optional[Tuple[str, str]]:
        """
        Extract skill information from TiddlyWiki image markup.
        
        Args:
            skill_text: Raw skill text like "[img width=24 [Fire Grab|URL]]-Fire Grab"
            
        Returns:
            Tuple of (skill_name, icon_url) or None
        """
        match = self.skill_pattern.search(skill_text)
        if match:
            skill_name = match.group(1)
            icon_url = match.group(2)
            return skill_name, icon_url
        return None
    
    def extract_score_value(self, score_text: str) -> float:
        """
        Extract numeric score from text, handling commas and decimals.
        
        Args:
            score_text: Raw score text like "20,965.00"
            
        Returns:
            Float value of the score
        """
        # Remove commas and extract numeric value
        clean_score = re.sub(r'[,\s]', '', score_text.strip())
        try:
            return float(clean_score)
        except ValueError:
            return 0.0
    
    def parse_table_section(self, section_text: str, metric_type: str, timestamp: str) -> List[HighScoreEntry]:
        """
        Parse a single table section for a specific metric.
        
        Args:
            section_text: Raw HTML text containing the table
            metric_type: Type of metric being parsed
            timestamp: Timestamp for the log file
            
        Returns:
            List of HighScoreEntry objects
        """
        entries = []
        
        # Split by table rows, skip header rows
        lines = section_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('|@@') or line.startswith('| \'\''):
                continue
            
            # Parse table row: |player|skill|score| or |player|score|
            if line.startswith('|') and line.endswith('|'):
                # For skill damage tables, we need to handle the pipe in URLs more carefully
                # Pattern: |<span...>-N|[img...|URL]]-SkillName | Score|
                
                # Extract player info first
                player_match = self.player_pattern.search(line)
                if not player_match:
                    continue
                
                account_name = player_match.group(1)
                profession = player_match.group(2)
                display_name = player_match.group(3).strip()
                fight_number = int(player_match.group(4))
                
                # Find the end of the player span
                player_end = line.find('</span>-' + str(fight_number))
                if player_end == -1:
                    continue
                player_end = line.find('|', player_end)
                
                # Extract the rest of the line after the player cell
                remaining = line[player_end + 1:].rstrip('|')
                
                # Check if this is a skill damage table (has image markup)
                if '[img width=24' in remaining:
                    # Find the last pipe before the score
                    last_pipe = remaining.rfind('|')
                    if last_pipe != -1:
                        skill_cell = remaining[:last_pipe].strip()
                        score_cell = remaining[last_pipe + 1:].strip()
                        
                        # Extract skill info
                        skill_info = self.extract_skill_info(skill_cell)
                        skill_name = skill_info[0] if skill_info else None
                        skill_icon_url = skill_info[1] if skill_info else None
                    else:
                        continue
                else:
                    # Simple two-column table |player|score|
                    score_cell = remaining.strip()
                    skill_name = None
                    skill_icon_url = None
                
                # Extract score value
                score_value = self.extract_score_value(score_cell)
                
                # Create entry
                entry = HighScoreEntry(
                    timestamp=timestamp,
                    player_account=account_name,
                    player_name=display_name,
                    profession=profession,
                    fight_number=fight_number,
                    metric_type=metric_type,
                    skill_name=skill_name,
                    skill_icon_url=skill_icon_url,
                    score_value=score_value
                )
                entries.append(entry)
        
        return entries
    
    def parse_high_scores_file(self, file_path: Path) -> List[HighScoreEntry]:
        """
        Parse a High-Scores.json file and extract all target metrics.
        
        Args:
            file_path: Path to the High-Scores.json file
            
        Returns:
            List of HighScoreEntry objects for all target metrics
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract timestamp from filename
            timestamp = file_path.stem.split('-')[0]
            
            # Get the HTML content
            html_content = data.get('text', '')
            
            all_entries = []
            
            # Split content into sections by finding each div with flex-col
            sections = html_content.split('<div class="flex-col">')
            
            for i, section in enumerate(sections):
                # Check if this section contains one of our target metrics
                for metric_name, metric_key in self.TARGET_METRICS.items():
                    pattern = f"''{metric_name}''"
                    if pattern in section:
                        # Parse this section
                        entries = self.parse_table_section(section, metric_key, timestamp)
                        all_entries.extend(entries)
                        break
            
            return all_entries
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return []
    
    def parse_directory(self, extracted_logs_dir: Path) -> List[HighScoreEntry]:
        """
        Parse all High-Scores.json files in an extracted_logs directory.
        
        Args:
            extracted_logs_dir: Path to the extracted_logs directory
            
        Returns:
            List of all HighScoreEntry objects from all files
        """
        all_entries = []
        
        # Find all High-Scores.json files
        high_scores_files = list(extracted_logs_dir.glob('*/*High-Scores.json'))
        
        print(f"Found {len(high_scores_files)} High-Scores.json files")
        
        for file_path in high_scores_files:
            entries = self.parse_high_scores_file(file_path)
            all_entries.extend(entries)
            print(f"Parsed {len(entries)} entries from {file_path.name}")
        
        return all_entries


def main():
    """Test the parser with a sample file"""
    parser = HighScoresParser()
    
    # Test with a specific file
    test_file = Path("extracted_logs/202506302308/202506302308-High-Scores.json")
    if test_file.exists():
        entries = parser.parse_high_scores_file(test_file)
        print(f"Parsed {len(entries)} entries from test file")
        
        # Group by metric type
        by_metric = {}
        for entry in entries:
            if entry.metric_type not in by_metric:
                by_metric[entry.metric_type] = []
            by_metric[entry.metric_type].append(entry)
        
        # Show entries by metric type
        for metric_type, metric_entries in by_metric.items():
            print(f"\n{metric_type.upper()}: {len(metric_entries)} entries")
            for i, entry in enumerate(metric_entries[:3]):  # Show top 3
                print(f"  {i+1}. {entry.player_name} ({entry.profession}) - {entry.score_value}")
                if entry.skill_name:
                    print(f"     Skill: {entry.skill_name}")
    else:
        print("Test file not found")


if __name__ == "__main__":
    main()