# Daily Usage Guide

This guide covers routine operations for maintaining your GW2 WvW Leaderboard system once it's set up and running.

## Quick Reference Commands

```bash
# Check for new logs
python sync_logs.py --check-only

# Process new logs automatically  
python sync_logs.py --auto-confirm

# Manually regenerate UI
python generate_web_ui.py gw2_comprehensive.db -o web_ui_final

# Check database status
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"
```

## Daily Maintenance Routine

### 1. Check for New Combat Logs

**Automated (Recommended):**
```bash
# Check what's new
python sync_logs.py --check-only

# If new logs found, process them
python sync_logs.py --auto-confirm --max-logs 10
```

**Manual Alternative:**
If you have new TiddlyWiki files to process:
```bash
# Place files in extracted_logs/YYYYMMDDHHMM/ format
# Then parse them
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db
python glicko_rating_system.py gw2_comprehensive.db --recalculate
python generate_web_ui.py gw2_comprehensive.db -o web_ui_final
```

### 2. Monitor System Health

**Database Size:**
```bash
# Check number of sessions processed
sqlite3 gw2_comprehensive.db "SELECT COUNT(DISTINCT timestamp) FROM player_performances;"

# Check total player records
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"

# Check recent activity
sqlite3 gw2_comprehensive.db "SELECT timestamp, COUNT(*) as players FROM player_performances WHERE parsed_date >= date('now', '-7 days') GROUP BY timestamp ORDER BY timestamp DESC;"
```

**Disk Usage:**
```bash
# Check database file size
ls -lh gw2_comprehensive.db

# Check log directory size
du -sh extracted_logs/
```

### 3. Update Web Interface

If you made configuration changes or want to refresh the UI:
```bash
# Regenerate with current data
python generate_web_ui.py gw2_comprehensive.db -o web_ui_final

# Deploy to web server (example commands)
rsync -av web_ui_final/ user@server:/var/www/leaderboards/
# or
cp -r web_ui_final/* /path/to/your/webserver/
```

## Weekly Tasks

### 1. Review Performance Trends

Check the leaderboards for:
- New top performers in different metrics
- Shifts in profession effectiveness
- Participation trends over time

### 2. Backup Database

```bash
# Create timestamped backup
cp gw2_comprehensive.db "backups/gw2_leaderboard_$(date +%Y%m%d).db"

# Or compress for storage
gzip -c gw2_comprehensive.db > "backups/gw2_leaderboard_$(date +%Y%m%d).db.gz"
```

### 3. Clean Up Old Logs (Optional)

If disk space is a concern:
```bash
# Remove logs older than 6 months (example)
find extracted_logs/ -name "202[3-4]*" -type d -exec rm -rf {} \;

# Or compress old logs
find extracted_logs/ -name "202[3-4]*" -type d -exec tar -czf {}.tar.gz {} \; -exec rm -rf {} \;
```

## Configuration Management

### Sync Settings

Edit `sync_config.json` to adjust:

```json
{
  "log_aggregate_url": "https://pyrogw2.github.io",
  "database_path": "gw2_comprehensive.db", 
  "extracted_logs_dir": "extracted_logs",
  "web_ui_output": "web_ui_final",
  "auto_confirm": false,              // Set to true for full automation
  "max_logs_per_run": 5               // Increase for bulk processing
}
```

### Profession Weightings

To adjust how professions are ranked, edit `glicko_rating_system.py`:

```python
PROFESSION_METRICS = {
    'Firebrand': {
        'DPS': 0.3,           # Increase for more DPS weight
        'Healing': 0.25,      # Adjust support focus
        'Barrier': 0.2,
        'Cleanses': 0.1, 
        'Stability': 0.15
    },
    # ... other professions
}
```

After changes, recalculate ratings:
```bash
python glicko_rating_system.py gw2_comprehensive.db --recalculate
python generate_web_ui.py gw2_comprehensive.db -o web_ui_final
```

## Troubleshooting Common Issues

### Sync Problems

**No new logs found:**
```bash
# Check the aggregate site manually
curl -s https://pyrogw2.github.io | grep -o '"title":"[^"]*202[0-9]*[^"]*"' | head -5

# Verify sync config
cat sync_config.json

# Test connectivity
python -c "import requests; print(requests.get('https://pyrogw2.github.io').status_code)"
```

**Download failures:**
```bash
# Try with more verbose output
python sync_logs.py --check-only

# Manual download test
wget https://pyrogw2.github.io -O test.html
```

### Database Issues

**Corruption detection:**
```bash
# Check database integrity
sqlite3 gw2_comprehensive.db "PRAGMA integrity_check;"

# Vacuum to reclaim space
sqlite3 gw2_comprehensive.db "VACUUM;"
```

**Missing data:**
```bash
# Check for recent data
sqlite3 gw2_comprehensive.db "SELECT MAX(parsed_date), COUNT(*) FROM player_performances;"

# Verify ratings exist
sqlite3 gw2_comprehensive.db "SELECT metric_category, COUNT(*) FROM glicko_ratings GROUP BY metric_category;"
```

### UI Generation Problems

**Empty leaderboards:**
```bash
# Verify source data
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM glicko_ratings WHERE metric_category = 'DPS';"

# Check for recent data
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances WHERE parsed_date >= date('now', '-30 days');"

# Regenerate everything
python glicko_rating_system.py gw2_comprehensive.db --recalculate
python generate_web_ui.py gw2_comprehensive.db -o web_ui_final
```

## Automation Scripts

### Simple Cron Job (Linux/macOS)

Add to crontab (`crontab -e`):
```bash
# Check for new logs every hour
0 * * * * cd /path/to/GW2LeaderBoard && python sync_logs.py --auto-confirm --max-logs 3 >> logs/sync.log 2>&1

# Full regeneration daily at 6 AM
0 6 * * * cd /path/to/GW2LeaderBoard && python generate_web_ui.py gw2_comprehensive.db -o web_ui_final >> logs/daily.log 2>&1
```

### Windows Task Scheduler

Create batch file `update_leaderboards.bat`:
```batch
@echo off
cd /d "C:\path\to\GW2LeaderBoard"
python sync_logs.py --auto-confirm --max-logs 3
if %errorlevel% equ 0 (
    echo Update successful
) else (
    echo Update failed
)
```

Schedule to run hourly via Task Scheduler.

### GitHub Actions (for public repositories)

Create `.github/workflows/update-leaderboards.yml`:
```yaml
name: Update Leaderboards
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:        # Manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install requests
      - name: Update leaderboards
        run: |
          python sync_logs.py --auto-confirm --max-logs 5
          python generate_web_ui.py gw2_comprehensive.db -o web_ui_final
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./web_ui_final
```

## Performance Optimization

### For Large Datasets

**Database optimization:**
```bash
# Add indexes for common queries
sqlite3 gw2_comprehensive.db "CREATE INDEX IF NOT EXISTS idx_parsed_date ON player_performances(parsed_date);"
sqlite3 gw2_comprehensive.db "CREATE INDEX IF NOT EXISTS idx_timestamp ON player_performances(timestamp);"
```

**Incremental processing:**
```bash
# Process only recent logs
python sync_logs.py --auto-confirm --max-logs 1

# Skip full recalculation if only adding recent data
python glicko_rating_system.py gw2_comprehensive.db --incremental
```

### Resource Monitoring

```bash
# Check Python memory usage during processing
/usr/bin/time -v python generate_web_ui.py gw2_comprehensive.db -o web_ui_final

# Monitor disk I/O
iotop -p $(pgrep python)
```

## Deployment Strategies

### Static Hosting

**GitHub Pages:**
1. Push `web_ui_final/` contents to `gh-pages` branch
2. Enable GitHub Pages in repository settings
3. Access at `https://username.github.io/repository-name/`

**Netlify:**
1. Connect repository to Netlify
2. Set build command: `python generate_web_ui.py gw2_comprehensive.db -o web_ui_final`
3. Set publish directory: `web_ui_final/`

**Manual Upload:**
```bash
# Using rsync
rsync -av --delete web_ui_final/ user@server:/var/www/leaderboards/

# Using SCP
scp -r web_ui_final/* user@server:/var/www/leaderboards/
```

## Monitoring and Alerts

### Health Check Script

Create `health_check.py`:
```python
#!/usr/bin/env python3
import sqlite3
import sys
from datetime import datetime, timedelta

db_path = 'gw2_comprehensive.db'
conn = sqlite3.connect(db_path)

# Check recent activity
cutoff = datetime.now() - timedelta(days=7)
cursor = conn.execute(
    "SELECT COUNT(*) FROM player_performances WHERE parsed_date >= ?", 
    (cutoff.isoformat(),)
)
recent_count = cursor.fetchone()[0]

if recent_count == 0:
    print("WARNING: No recent data in past 7 days")
    sys.exit(1)
else:
    print(f"OK: {recent_count} recent records found")
    sys.exit(0)
```

Use in monitoring systems or cron jobs for alerts.