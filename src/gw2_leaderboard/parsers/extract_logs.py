#!/usr/bin/env python3
"""
Extract individual GW2 log summaries from TiddlyWiki HTML file.
"""

import json
import re
import os
from pathlib import Path
from bs4 import BeautifulSoup
import argparse


def extract_tiddler_data(html_file_path):
    """Extract tiddler data from TiddlyWiki HTML file."""
    print(f"Reading {html_file_path}...")
    
    with open(html_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the tiddler store script tag
    soup = BeautifulSoup(content, 'html.parser')
    tiddler_store = soup.find('script', {'class': 'tiddlywiki-tiddler-store'})
    
    if not tiddler_store:
        raise ValueError("Could not find tiddler store in HTML file")
    
    # Parse the JSON data
    tiddler_data = json.loads(tiddler_store.string)
    print(f"Found {len(tiddler_data)} tiddlers")
    
    return tiddler_data


def extract_log_summaries(tiddler_data, output_dir):
    """Extract individual log summaries and related tiddlers."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Pattern to match log summary timestamps
    log_pattern = re.compile(r'^(\d{12})-Log-Summary$')
    
    # Find all log summaries
    log_summaries = []
    for tiddler in tiddler_data:
        title = tiddler.get('title', '')
        match = log_pattern.match(title)
        if match:
            timestamp = match.group(1)
            log_summaries.append((timestamp, tiddler))
    
    print(f"Found {len(log_summaries)} log summaries")
    
    # Group all tiddlers by timestamp
    tiddler_groups = {}
    for tiddler in tiddler_data:
        title = tiddler.get('title', '')
        # Check if this tiddler belongs to a log session
        for timestamp, _ in log_summaries:
            if title.startswith(timestamp):
                if timestamp not in tiddler_groups:
                    tiddler_groups[timestamp] = []
                tiddler_groups[timestamp].append(tiddler)
                break
    
    # Extract each log session
    for timestamp, main_tiddler in log_summaries:
        log_dir = output_path / timestamp
        log_dir.mkdir(exist_ok=True)
        
        # Get all related tiddlers for this timestamp
        related_tiddlers = tiddler_groups.get(timestamp, [])
        
        print(f"Extracting {timestamp}: {len(related_tiddlers)} tiddlers")
        
        # Save each tiddler as a separate file
        for tiddler in related_tiddlers:
            tiddler_title = tiddler.get('title', '')
            # Clean filename
            filename = re.sub(r'[^\w\-_.]', '_', tiddler_title) + '.json'
            
            with open(log_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(tiddler, f, indent=2, ensure_ascii=False)
        
        # Create a summary info file
        summary_info = {
            'timestamp': timestamp,
            'main_tiddler': main_tiddler.get('title'),
            'tiddler_count': len(related_tiddlers),
            'tiddler_titles': [t.get('title') for t in related_tiddlers],
            'created': main_tiddler.get('created'),
            'modified': main_tiddler.get('modified')
        }
        
        with open(log_dir / 'summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary_info, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='Extract GW2 log summaries from TiddlyWiki')
    parser.add_argument('input_file', help='Path to TiddlyWiki HTML file')
    parser.add_argument('-o', '--output', default='extracted_logs', 
                        help='Output directory (default: extracted_logs)')
    
    args = parser.parse_args()
    
    try:
        tiddler_data = extract_tiddler_data(args.input_file)
        extract_log_summaries(tiddler_data, args.output)
        print(f"Extraction complete! Check {args.output} directory.")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())