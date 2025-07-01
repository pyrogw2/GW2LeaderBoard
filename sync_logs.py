#!/usr/bin/env python3
"""
Automated log synchronization script for GW2 WvW Leaderboards.
Fetches new logs from the configured aggregate site, processes them, and updates the leaderboard.
"""

import json
import requests
import sqlite3
import argparse
import sys
import os
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
import subprocess

# Configuration
DEFAULT_CONFIG = {
    "log_aggregate_url": "https://pyrogw2.github.io",
    "database_path": "gw2_comprehensive.db",
    "extracted_logs_dir": "extracted_logs",
    "web_ui_output": "web_ui_final",
    "auto_confirm": False,  # Set to True to skip confirmation prompts
    "max_logs_per_run": 5   # Limit new logs to prevent overwhelming
}

CONFIG_FILE = "sync_config.json"


def load_config() -> Dict:
    """Load configuration from file or create default."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Merge with defaults for any missing keys
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        return config
    else:
        # Create default config file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"📄 Created default configuration file: {CONFIG_FILE}")
        print("📝 Edit this file to customize settings.")
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict):
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


def get_existing_logs(extracted_logs_dir: str) -> Set[str]:
    """Get set of existing log timestamps."""
    logs_path = Path(extracted_logs_dir)
    if not logs_path.exists():
        return set()
    
    existing = set()
    for item in logs_path.iterdir():
        if item.is_dir() and re.match(r'^\d{12}$', item.name):
            existing.add(item.name)
    
    return existing


def fetch_available_logs(base_url: str) -> List[Dict]:
    """Fetch list of available logs from the aggregate site."""
    print(f"🌐 Fetching log list from {base_url}...")
    
    try:
        response = requests.get(base_url, timeout=30)
        response.raise_for_status()
        content = response.text
        
        # Check if this is a TiddlyWiki site
        if 'tiddlywiki' in content.lower() or 'tiddler' in content.lower():
            return fetch_logs_from_tiddlywiki(base_url, content)
        else:
            return fetch_logs_from_static_site(base_url, content)
            
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        return []


def fetch_logs_from_tiddlywiki(base_url: str, content: str) -> List[Dict]:
    """Extract log information from TiddlyWiki site."""
    print("📜 Detected TiddlyWiki site, extracting tiddler information...")
    
    available_logs = []
    
    # Look for tiddler data with timestamps
    # TiddlyWiki stores data in JSON format within the HTML
    patterns = [
        # Look for timestamp patterns in tiddler titles or content
        r'"title":"([^"]*(\d{12})[^"]*)"',
        r'"(\d{12})"[^}]*"title"',
        # Look for tiddlers that might contain log data
        r'"title":"([^"]*(?:log|summary|session)[^"]*(\d{8,12})[^"]*)"'
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) >= 2:
                title = match.group(1)
                timestamp_text = match.group(2)
            else:
                title = match.group(1)
                # Extract timestamp from title
                timestamp_match = re.search(r'(\d{12})', title)
                if not timestamp_match:
                    continue
                timestamp_text = timestamp_match.group(1)
            
            # Validate timestamp format (YYYYMMDDHHMM)
            if len(timestamp_text) == 12 and timestamp_text.isdigit():
                # For TiddlyWiki, we'll need to construct export URLs
                # This assumes the site supports exporting individual tiddlers
                export_url = f"{base_url}#{title}"
                
                log_info = {
                    'timestamp': timestamp_text,
                    'url': export_url,
                    'filename': f"{timestamp_text}_tiddler.json",
                    'source_page': base_url,
                    'tiddler_title': title,
                    'is_tiddlywiki': True
                }
                
                # Avoid duplicates
                if not any(log['timestamp'] == timestamp_text for log in available_logs):
                    available_logs.append(log_info)
    
    # Sort by timestamp (newest first)
    available_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    print(f"📋 Found {len(available_logs)} log tiddlers in TiddlyWiki")
    return available_logs


def fetch_logs_from_static_site(base_url: str, content: str) -> List[Dict]:
    """Extract log information from static site."""
    print("🗂️  Scanning static site for log files...")
    
    available_logs = []
    
    # Look for downloadable log files
    patterns = [
        r'href=["\']([^"\']*(\d{12})[^"\']*\.(?:html|zip|tw|json))["\']',  # Timestamped files
        r'href=["\']([^"\']*log[^"\']*\.(?:html|zip|tw|json))["\']',       # Files with "log" in name
        r'href=["\']([^"\']*(?:2025|2024)\d{8}[^"\']*)["\']',            # Files with date patterns
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            file_url = match.group(1)
            
            # Extract timestamp if possible
            timestamp_match = re.search(r'(\d{12})', file_url)
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                
                # Make URL absolute
                if not file_url.startswith('http'):
                    file_url = urljoin(base_url, file_url)
                
                log_info = {
                    'timestamp': timestamp,
                    'url': file_url,
                    'filename': os.path.basename(urlparse(file_url).path),
                    'source_page': base_url,
                    'is_tiddlywiki': False
                }
                
                # Avoid duplicates
                if not any(log['timestamp'] == timestamp for log in available_logs):
                    available_logs.append(log_info)
    
    # Sort by timestamp (newest first)
    available_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    print(f"📋 Found {len(available_logs)} available logs")
    return available_logs


def download_and_extract_log(log_info: Dict, extracted_logs_dir: str) -> bool:
    """Download and extract a log file."""
    timestamp = log_info['timestamp']
    url = log_info['url']
    filename = log_info['filename']
    
    print(f"📥 Processing {filename}...")
    
    try:
        # Create extraction directory
        extract_dir = Path(extracted_logs_dir) / timestamp
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        if log_info.get('is_tiddlywiki', False):
            # This is a TiddlyWiki tiddler - need special handling
            return extract_tiddlywiki_tiddler(log_info, str(extract_dir))
        
        # Regular file download
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        # Download to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            if filename.lower().endswith('.zip'):
                # Extract ZIP file
                print(f"📦 Extracting ZIP file to {extract_dir}...")
                with zipfile.ZipFile(tmp_file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            
            elif filename.lower().endswith(('.html', '.tw')):
                # TiddlyWiki file - use existing extraction logic
                print(f"📜 Processing TiddlyWiki file...")
                
                # Save TiddlyWiki file
                tw_path = extract_dir / f"{timestamp}.html"
                shutil.copy2(tmp_file_path, tw_path)
                
                # Extract using existing extract_logs.py if available
                if Path("extract_logs.py").exists():
                    result = subprocess.run([
                        sys.executable, "extract_logs.py", 
                        str(tw_path), 
                        "-o", str(extract_dir)
                    ], capture_output=True, text=True)
                    
                    if result.returncode != 0:
                        print(f"⚠️  Extraction script failed: {result.stderr}")
                        # Try manual extraction by looking for JSON data
                        extract_json_from_tiddlywiki(str(tw_path), str(extract_dir))
                else:
                    # Manual extraction
                    extract_json_from_tiddlywiki(str(tw_path), str(extract_dir))
            
            else:
                print(f"⚠️  Unknown file format: {filename}")
                return False
            
            # Verify extraction
            json_files = list(extract_dir.glob("*.json"))
            if json_files:
                print(f"✅ Successfully extracted {len(json_files)} JSON files")
                return True
            else:
                print(f"❌ No JSON files found after extraction")
                return False
                
        finally:
            # Clean up temp file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        print(f"❌ Failed to process {filename}: {e}")
        return False


def extract_tiddlywiki_tiddler(log_info: Dict, extract_dir: str) -> bool:
    """Extract data from a specific TiddlyWiki tiddler."""
    print(f"📜 Extracting TiddlyWiki tiddler: {log_info.get('tiddler_title', 'Unknown')}")
    
    try:
        # For TiddlyWiki sites, we need to fetch the whole site and extract the specific tiddler
        base_url = log_info['source_page']
        response = requests.get(base_url, timeout=60)
        response.raise_for_status()
        
        content = response.text
        tiddler_title = log_info.get('tiddler_title', '')
        
        # Look for the specific tiddler in the TiddlyWiki content
        # TiddlyWiki stores tiddlers as JSON objects
        tiddler_pattern = rf'"title":"{re.escape(tiddler_title)}"[^{{}}]*"text":"([^"]*)"'
        
        match = re.search(tiddler_pattern, content)
        if match:
            tiddler_text = match.group(1)
            
            # Decode JSON escapes
            tiddler_text = tiddler_text.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            
            # If the tiddler text is JSON, save it
            try:
                tiddler_data = json.loads(tiddler_text)
                
                # Save as JSON file
                output_file = Path(extract_dir) / f"{log_info['timestamp']}-tiddler.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(tiddler_data, f, indent=2)
                
                print(f"✅ Extracted tiddler data to {output_file}")
                return True
                
            except json.JSONDecodeError:
                # Maybe it's not JSON, try to extract JSON from the text
                return extract_json_from_text(tiddler_text, extract_dir, log_info['timestamp'])
        
        # Fallback: look for any tiddlers with the timestamp
        return extract_json_from_tiddlywiki_by_timestamp(content, extract_dir, log_info['timestamp'])
        
    except Exception as e:
        print(f"❌ Failed to extract TiddlyWiki tiddler: {e}")
        return False


def extract_json_from_text(text: str, extract_dir: str, timestamp: str) -> bool:
    """Extract JSON data from text content."""
    json_objects = []
    
    # Look for JSON-like structures
    brace_count = 0
    start_pos = None
    
    for i, char in enumerate(text):
        if char == '{':
            if brace_count == 0:
                start_pos = i
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0 and start_pos is not None:
                json_text = text[start_pos:i+1]
                try:
                    json_obj = json.loads(json_text)
                    json_objects.append(json_obj)
                except json.JSONDecodeError:
                    pass
                start_pos = None
    
    if json_objects:
        for i, obj in enumerate(json_objects):
            output_file = Path(extract_dir) / f"{timestamp}-extracted-{i}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(obj, f, indent=2)
        
        print(f"✅ Extracted {len(json_objects)} JSON objects")
        return True
    
    return False


def extract_json_from_tiddlywiki_by_timestamp(content: str, extract_dir: str, timestamp: str) -> bool:
    """Extract JSON data from TiddlyWiki by looking for timestamp-related tiddlers."""
    print(f"🔍 Searching for tiddlers with timestamp {timestamp}...")
    
    # Look for any tiddlers that might contain the log data
    patterns = [
        rf'"title":"[^"]*{timestamp}[^"]*"[^{{}}]*"text":"([^"]*)"',
        rf'"title":"[^"]*{timestamp[:8]}[^"]*"[^{{}}]*"text":"([^"]*)"',  # Date only
    ]
    
    extracted_count = 0
    
    for pattern in patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            try:
                tiddler_text = match.group(1)
                # Decode JSON escapes
                tiddler_text = tiddler_text.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
                
                # Try to parse as JSON
                try:
                    tiddler_data = json.loads(tiddler_text)
                    
                    output_file = Path(extract_dir) / f"{timestamp}-tiddler-{extracted_count}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(tiddler_data, f, indent=2)
                    
                    extracted_count += 1
                    
                except json.JSONDecodeError:
                    # Try to extract JSON from within the text
                    if extract_json_from_text(tiddler_text, extract_dir, f"{timestamp}-{extracted_count}"):
                        extracted_count += 1
                        
            except Exception:
                continue
    
    if extracted_count > 0:
        print(f"✅ Extracted {extracted_count} tiddlers")
        return True
    
    print("❌ No tiddler data found")
    return False


def extract_json_from_tiddlywiki(tw_path: str, output_dir: str):
    """Extract JSON data from TiddlyWiki file manually."""
    print("🔍 Attempting manual JSON extraction from TiddlyWiki...")
    
    try:
        with open(tw_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Look for JSON data blocks in the TiddlyWiki
        json_pattern = r'<div[^>]*title="([^"]*)"[^>]*type="application/json"[^>]*>(.*?)</div>'
        
        matches = re.finditer(json_pattern, content, re.DOTALL)
        extracted_count = 0
        
        for match in matches:
            title = match.group(1)
            json_data = match.group(2).strip()
            
            # Clean up the JSON data
            json_data = json_data.replace('&lt;', '<').replace('&gt;', '>')
            json_data = json_data.replace('&amp;', '&').replace('&quot;', '"')
            
            try:
                # Validate JSON
                parsed = json.loads(json_data)
                
                # Save to file
                safe_title = re.sub(r'[^\w\-_.]', '_', title)
                output_file = Path(output_dir) / f"{safe_title}.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(parsed, f, indent=2)
                
                extracted_count += 1
                
            except json.JSONDecodeError:
                continue
        
        if extracted_count > 0:
            print(f"✅ Manually extracted {extracted_count} JSON files")
        else:
            print("❌ Could not extract JSON data from TiddlyWiki")
            
    except Exception as e:
        print(f"❌ Manual extraction failed: {e}")


def process_new_logs(extracted_logs_dir: str, database_path: str):
    """Process newly downloaded logs through the pipeline."""
    print("🔄 Processing new logs through pipeline...")
    
    steps = [
        {
            'name': 'Parse logs',
            'script': 'parse_logs_enhanced.py',
            'args': [extracted_logs_dir, '-d', database_path]
        },
        {
            'name': 'Recalculate Glicko ratings',
            'script': 'glicko_rating_system.py',
            'args': [database_path, '--recalculate']
        }
    ]
    
    for step in steps:
        print(f"📊 {step['name']}...")
        
        if not Path(step['script']).exists():
            print(f"❌ Script not found: {step['script']}")
            return False
        
        result = subprocess.run([
            sys.executable, step['script']] + step['args'], 
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"❌ {step['name']} failed:")
            print(result.stderr)
            return False
        else:
            print(f"✅ {step['name']} completed")
    
    return True


def generate_web_ui(database_path: str, output_dir: str):
    """Generate the web UI."""
    print("🌐 Generating web UI...")
    
    if not Path("generate_web_ui.py").exists():
        print("❌ Web UI generator not found: generate_web_ui.py")
        return False
    
    result = subprocess.run([
        sys.executable, "generate_web_ui.py", 
        database_path, "-o", output_dir
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Web UI generation failed:")
        print(result.stderr)
        return False
    else:
        print(f"✅ Web UI generated in {output_dir}")
        return True


def main():
    global CONFIG_FILE
    
    parser = argparse.ArgumentParser(description="Sync logs and update leaderboards")
    parser.add_argument("--config", help="Path to config file", default=CONFIG_FILE)
    parser.add_argument("--check-only", action="store_true", help="Only check for new logs, don't download")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip confirmation prompts")
    parser.add_argument("--max-logs", type=int, help="Maximum number of new logs to process")
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config != CONFIG_FILE:
        CONFIG_FILE = args.config
    
    config = load_config()
    
    # Override config with command line args
    if args.auto_confirm:
        config["auto_confirm"] = True
    if args.max_logs:
        config["max_logs_per_run"] = args.max_logs
    
    print("🏆 GW2 WvW Leaderboard Log Sync")
    print("=" * 40)
    print(f"📍 Log source: {config['log_aggregate_url']}")
    print(f"💾 Database: {config['database_path']}")
    print(f"📁 Extract to: {config['extracted_logs_dir']}")
    print()
    
    # Get existing logs
    existing_logs = get_existing_logs(config["extracted_logs_dir"])
    print(f"📋 Found {len(existing_logs)} existing logs")
    
    # Fetch available logs
    available_logs = fetch_available_logs(config["log_aggregate_url"])
    
    if not available_logs:
        print("❌ No logs found on the aggregate site")
        return 1
    
    # Find new logs
    new_logs = [log for log in available_logs if log['timestamp'] not in existing_logs]
    
    if not new_logs:
        print("✅ No new logs found. All logs are up to date!")
        return 0
    
    # Limit new logs
    if len(new_logs) > config["max_logs_per_run"]:
        print(f"📊 Found {len(new_logs)} new logs, limiting to {config['max_logs_per_run']}")
        new_logs = new_logs[:config["max_logs_per_run"]]
    
    print(f"\n🆕 Found {len(new_logs)} new logs:")
    for i, log in enumerate(new_logs, 1):
        timestamp = log['timestamp']
        # Format timestamp for display
        try:
            dt = datetime.strptime(timestamp, '%Y%m%d%H%M')
            formatted_date = dt.strftime('%Y-%m-%d %H:%M')
        except:
            formatted_date = timestamp
        
        print(f"  {i}. {log['filename']} ({formatted_date})")
    
    if args.check_only:
        print("\n👀 Check-only mode. Exiting without downloading.")
        return 0
    
    # Confirm download
    if not config["auto_confirm"]:
        response = input(f"\n❓ Download and process {len(new_logs)} new logs? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Cancelled by user")
            return 0
    
    # Download and process new logs
    success_count = 0
    
    for i, log in enumerate(new_logs, 1):
        print(f"\n📦 Processing log {i}/{len(new_logs)}: {log['filename']}")
        
        if download_and_extract_log(log, config["extracted_logs_dir"]):
            success_count += 1
        else:
            print(f"❌ Failed to process {log['filename']}")
    
    if success_count == 0:
        print("❌ No logs were successfully processed")
        return 1
    
    print(f"\n✅ Successfully downloaded {success_count}/{len(new_logs)} logs")
    
    # Process logs through pipeline
    if process_new_logs(config["extracted_logs_dir"], config["database_path"]):
        print("✅ Log processing pipeline completed")
        
        # Generate web UI
        if generate_web_ui(config["database_path"], config["web_ui_output"]):
            print("✅ Web UI updated")
            print(f"\n🎉 Sync complete! Open {config['web_ui_output']}/index.html to view updated leaderboards")
            return 0
        else:
            print("❌ Web UI generation failed")
            return 1
    else:
        print("❌ Log processing pipeline failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())