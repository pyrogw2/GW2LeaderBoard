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
        # Try common patterns for log listing
        possible_endpoints = [
            "",  # Root page
            "/logs/",
            "/index.html",
            "/logs.json",  # If they have a JSON API
        ]
        
        available_logs = []
        
        for endpoint in possible_endpoints:
            url = urljoin(base_url.rstrip('/') + '/', endpoint.lstrip('/'))
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    content = response.text
                    
                    # Look for downloadable log files
                    # Pattern for TiddlyWiki log files or zip archives
                    patterns = [
                        r'href=["\']([^"\']*(\d{12})[^"\']*\.(?:html|zip|tw))["\']',  # Timestamped files
                        r'href=["\']([^"\']*log[^"\']*\.(?:html|zip|tw))["\']',       # Files with "log" in name
                        r'href=["\']([^"\']*(?:2025|2024)\d{8}[^"\']*)["\']',        # Files with date patterns
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
                                    file_url = urljoin(url, file_url)
                                
                                log_info = {
                                    'timestamp': timestamp,
                                    'url': file_url,
                                    'filename': os.path.basename(urlparse(file_url).path),
                                    'source_page': url
                                }
                                
                                # Avoid duplicates
                                if not any(log['timestamp'] == timestamp for log in available_logs):
                                    available_logs.append(log_info)
                
                if available_logs:
                    break  # Found logs, no need to try other endpoints
                    
            except requests.RequestException as e:
                print(f"⚠️  Failed to fetch {url}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        available_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        print(f"📋 Found {len(available_logs)} available logs")
        return available_logs
        
    except Exception as e:
        print(f"❌ Error fetching logs: {e}")
        return []


def download_and_extract_log(log_info: Dict, extracted_logs_dir: str) -> bool:
    """Download and extract a log file."""
    timestamp = log_info['timestamp']
    url = log_info['url']
    filename = log_info['filename']
    
    print(f"📥 Downloading {filename}...")
    
    try:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        # Create extraction directory
        extract_dir = Path(extracted_logs_dir) / timestamp
        extract_dir.mkdir(parents=True, exist_ok=True)
        
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
        print(f"❌ Failed to download/extract {filename}: {e}")
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