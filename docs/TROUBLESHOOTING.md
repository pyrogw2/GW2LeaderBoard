# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the GW2 WvW Leaderboard system.

## Quick Diagnostic Commands

```bash
# Check database status
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"
sqlite3 gw2_comprehensive.db "SELECT COUNT(DISTINCT metric_category) FROM glicko_ratings;"

# Check recent data
sqlite3 gw2_comprehensive.db "SELECT MAX(parsed_date), COUNT(*) FROM player_performances;"

# Test web generation
python generate_web_ui.py gw2_comprehensive.db -o test_output

# Check sync configuration
cat sync_config.json

# Test network connectivity
python -c "import requests; print(requests.get('https://pyrogw2.github.io').status_code)"
```

## Common Issues and Solutions

### 1. Database Problems

#### "Database is locked" Error

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Causes:**
- Another process is accessing the database
- Previous process crashed without releasing lock
- Database file permissions issue

**Solutions:**
```bash
# Check for running processes
ps aux | grep python
ps aux | grep sqlite

# Kill hanging processes
pkill -f "python.*parse_logs"
pkill -f "python.*glicko"

# Check file permissions
ls -la gw2_comprehensive.db
chmod 664 gw2_comprehensive.db

# Test database integrity
sqlite3 gw2_comprehensive.db "PRAGMA integrity_check;"
```

#### "No such column" Errors

**Symptoms:**
```
sqlite3.OperationalError: no such column: down_contribution_per_sec
```

**Causes:**
- Database schema is outdated
- Columns were added after database creation
- Database corruption

**Solutions:**
```bash
# Check current schema
sqlite3 gw2_comprehensive.db ".schema player_performances"

# Option 1: Add missing columns manually
sqlite3 gw2_comprehensive.db "ALTER TABLE player_performances ADD COLUMN down_contribution_per_sec REAL DEFAULT 0.0;"

# Option 2: Recreate database (loses data)
rm gw2_comprehensive.db
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db

# Option 3: Export and reimport data
sqlite3 gw2_comprehensive.db ".dump" > backup.sql
rm gw2_comprehensive.db
sqlite3 gw2_comprehensive.db ".read backup.sql"
```

#### Empty Database

**Symptoms:**
- Database exists but has no data
- Query returns 0 rows

**Diagnosis:**
```bash
# Check table existence
sqlite3 gw2_comprehensive.db ".tables"

# Check table schemas
sqlite3 gw2_comprehensive.db ".schema"

# Check for any data
sqlite3 gw2_comprehensive.db "SELECT name, COUNT(*) FROM (SELECT 'player_performances' as name UNION SELECT 'glicko_ratings' as name) LEFT JOIN player_performances ON 1=1 LEFT JOIN glicko_ratings ON 1=1;"
```

**Solutions:**
```bash
# Reparse logs
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db

# Check log directory structure
ls -la extracted_logs/
ls -la extracted_logs/*/

# Verify log file format
head -20 extracted_logs/*/summary.json
```

### 2. Log Parsing Issues

#### No Logs Found

**Symptoms:**
```
📁 Found 0 log directories
No combat sessions found
```

**Diagnosis:**
```bash
# Check directory structure
ls -la extracted_logs/
find extracted_logs/ -name "*.json" | head -10

# Check directory naming
ls extracted_logs/ | grep -E '^[0-9]{12}$'
```

**Solutions:**
```bash
# Correct directory structure should be:
mkdir -p extracted_logs/202506302308
# Place JSON files in the timestamp directory

# Check for hidden files or wrong permissions
ls -la extracted_logs/*/
chmod -R 755 extracted_logs/
```

#### Malformed Log Data

**Symptoms:**
```
JSON decode error
KeyError: 'offensive_stats'
No valid performance data found
```

**Diagnosis:**
```bash
# Check JSON validity
python -m json.tool extracted_logs/202506302308/summary.json

# Look for required fields
grep -l "offensive_stats" extracted_logs/*/*.json
grep -l "totalDmg" extracted_logs/*/*.json
```

**Solutions:**
```bash
# Re-extract from TiddlyWiki source
python extract_logs.py source.html -o extracted_logs/

# Manually verify log structure
cat extracted_logs/202506302308/*Offensive*.json | head -50

# Skip problematic logs
rm -rf extracted_logs/problematic_timestamp/
```

### 3. Rating System Problems

#### No Glicko Ratings Generated

**Symptoms:**
- `glicko_ratings` table is empty
- Web UI shows "No data available"

**Diagnosis:**
```bash
# Check if performance data exists
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"

# Check for sufficient data per session
sqlite3 gw2_comprehensive.db "SELECT timestamp, COUNT(*) as players FROM player_performances GROUP BY timestamp HAVING players >= 5;"

# Check metric values
sqlite3 gw2_comprehensive.db "SELECT AVG(target_dps), COUNT(*) FROM player_performances WHERE target_dps > 0;"
```

**Solutions:**
```bash
# Force recalculation
python glicko_rating_system.py gw2_comprehensive.db --recalculate

# Check minimum requirements
# Edit glicko_rating_system.py to lower MIN_PLAYERS_PER_SESSION if needed

# Verify data quality
sqlite3 gw2_comprehensive.db "SELECT timestamp, COUNT(*), AVG(target_dps) FROM player_performances WHERE target_dps > 0 GROUP BY timestamp;"
```

#### Extreme or Invalid Ratings

**Symptoms:**
- Ratings much higher or lower than expected (outside 800-2500 range)
- NaN or infinite values in ratings

**Diagnosis:**
```bash
# Check rating ranges
sqlite3 gw2_comprehensive.db "SELECT metric_category, MIN(rating), MAX(rating), AVG(rating) FROM glicko_ratings GROUP BY metric_category;"

# Look for outliers in source data
sqlite3 gw2_comprehensive.db "SELECT account_name, target_dps FROM player_performances WHERE target_dps > 10000 ORDER BY target_dps DESC LIMIT 10;"

# Check for zero standard deviations
python -c "
import sqlite3
conn = sqlite3.connect('gw2_comprehensive.db')
cursor = conn.execute('SELECT timestamp, COUNT(*), AVG(target_dps), MIN(target_dps), MAX(target_dps) FROM player_performances WHERE target_dps > 0 GROUP BY timestamp')
for row in cursor:
    timestamp, count, avg, min_val, max_val = row
    if min_val == max_val and count > 1:
        print(f'Zero variance in {timestamp}: {count} players all have {min_val} DPS')
"
```

**Solutions:**
```bash
# Remove outlier data
sqlite3 gw2_comprehensive.db "DELETE FROM player_performances WHERE target_dps > 20000;"

# Recalculate ratings
python glicko_rating_system.py gw2_comprehensive.db --recalculate

# Add data validation to parser
# Edit parse_logs_enhanced.py to add bounds checking
```

### 4. Web UI Generation Issues

#### Empty Leaderboards

**Symptoms:**
- Web page loads but shows "No data available"
- Tables are empty or missing

**Diagnosis:**
```bash
# Check data generation
python generate_web_ui.py gw2_comprehensive.db -o debug_output

# Verify rating data exists
sqlite3 gw2_comprehensive.db "SELECT metric_category, COUNT(*) FROM glicko_ratings GROUP BY metric_category;"

# Check JavaScript console in browser for errors
# Open browser developer tools (F12)
```

**Solutions:**
```bash
# Regenerate ratings first
python glicko_rating_system.py gw2_comprehensive.db --recalculate

# Then regenerate UI
python generate_web_ui.py gw2_comprehensive.db -o web_ui_output

# Check output files
ls -la web_ui_output/
head -20 web_ui_output/script.js
```

#### Missing Profession Icons

**Symptoms:**
- Broken image icons in profession columns
- Icons show as text abbreviations

**Diagnosis:**
```bash
# Check icon URLs in generated script
grep -n "profession_icons" web_ui_output/script.js

# Test icon URL accessibility
curl -I "https://wiki.guildwars2.com/images/..."
```

**Solutions:**
```bash
# Update icon URLs in generate_web_ui.py
# Look for profession_icons dictionary

# Clear browser cache
# Force refresh with Ctrl+F5

# Use local icons if external URLs are problematic
mkdir web_ui_output/icons/
# Download icons and update URLs to relative paths
```

#### Date Filtering Not Working

**Symptoms:**
- All time periods show same data
- Filter buttons don't change results

**Diagnosis:**
```bash
# Check if date-filtered data exists
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances WHERE parsed_date >= date('now', '-30 days');"

# Verify date format consistency
sqlite3 gw2_comprehensive.db "SELECT DISTINCT parsed_date FROM player_performances ORDER BY parsed_date LIMIT 10;"

# Check JavaScript errors in browser console
```

**Solutions:**
```bash
# Ensure parsed_date field is populated
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db

# Regenerate UI with date filtering
python generate_web_ui.py gw2_comprehensive.db -o web_ui_output

# Check date format in database
sqlite3 gw2_comprehensive.db "UPDATE player_performances SET parsed_date = date(substr(timestamp, 1, 4) || '-' || substr(timestamp, 5, 2) || '-' || substr(timestamp, 7, 2)) WHERE parsed_date IS NULL;"
```

### 5. Sync System Problems

#### No New Logs Detected

**Symptoms:**
```
📋 Found 0 available logs
No logs found on the aggregate site
```

**Diagnosis:**
```bash
# Test site connectivity
curl -s https://pyrogw2.github.io | head -20

# Check for TiddlyWiki structure
curl -s https://pyrogw2.github.io | grep -i tiddlywiki

# Look for timestamp patterns
curl -s https://pyrogw2.github.io | grep -o '"title":"[^"]*202[0-9]*[^"]*"' | head -10
```

**Solutions:**
```bash
# Update sync configuration
cat sync_config.json

# Try manual URL
python -c "
import requests
response = requests.get('https://pyrogw2.github.io')
print(f'Status: {response.status_code}')
print(f'Content length: {len(response.text)}')
print('Has TiddlyWiki:', 'tiddlywiki' in response.text.lower())
"

# Check timestamp extraction patterns
python sync_logs.py --check-only
```

#### Download Failures

**Symptoms:**
```
❌ Failed to download/extract filename.html
Request timeout
Connection error
```

**Diagnosis:**
```bash
# Test manual download
wget https://pyrogw2.github.io -O test.html

# Check network configuration
ping pyrogw2.github.io
nslookup pyrogw2.github.io

# Test with different timeout
python -c "
import requests
try:
    response = requests.get('https://pyrogw2.github.io', timeout=60)
    print(f'Success: {response.status_code}')
except Exception as e:
    print(f'Error: {e}')
"
```

**Solutions:**
```bash
# Increase timeout in sync_logs.py
# Edit the requests.get() calls to use timeout=120

# Use proxy if needed
export https_proxy=http://proxy.example.com:8080
python sync_logs.py --check-only

# Download manually and place in extracted_logs/
wget https://pyrogw2.github.io -O manual_log.html
python parse_logs_enhanced.py manual_log.html -d gw2_comprehensive.db
```

### 6. Performance Issues

#### Slow Processing

**Symptoms:**
- Rating calculations take very long
- UI generation times out
- High memory usage

**Diagnosis:**
```bash
# Check database size
ls -lh gw2_comprehensive.db

# Count records
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"
sqlite3 gw2_comprehensive.db "SELECT COUNT(DISTINCT timestamp) FROM player_performances;"

# Monitor resource usage
top -p $(pgrep python)
/usr/bin/time -v python glicko_rating_system.py gw2_comprehensive.db --recalculate
```

**Solutions:**
```bash
# Add database indexes
sqlite3 gw2_comprehensive.db "CREATE INDEX IF NOT EXISTS idx_timestamp ON player_performances(timestamp);"
sqlite3 gw2_comprehensive.db "CREATE INDEX IF NOT EXISTS idx_parsed_date ON player_performances(parsed_date);"

# Process in smaller batches
# Edit scripts to process sessions in chunks

# Clean up old data if needed
sqlite3 gw2_comprehensive.db "DELETE FROM player_performances WHERE parsed_date < date('now', '-365 days');"
sqlite3 gw2_comprehensive.db "VACUUM;"
```

#### Memory Errors

**Symptoms:**
```
MemoryError
Out of memory
System becomes unresponsive
```

**Solutions:**
```bash
# Increase available memory
# Close other applications

# Process data in smaller chunks
# Edit scripts to use iterative processing instead of loading all data

# Use database streaming
# Replace cursor.fetchall() with cursor.fetchone() in loops

# Monitor memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

## Prevention and Monitoring

### Health Checks

Create automated monitoring:

```bash
#!/bin/bash
# health_check.sh

# Check database accessibility
sqlite3 gw2_comprehensive.db "SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Database not accessible"
    exit 1
fi

# Check recent data
RECENT_COUNT=$(sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances WHERE parsed_date >= date('now', '-7 days');")
if [ "$RECENT_COUNT" -eq 0 ]; then
    echo "WARNING: No recent data (last 7 days)"
fi

# Check rating data
RATING_COUNT=$(sqlite3 gw2_comprehensive.db "SELECT COUNT(DISTINCT metric_category) FROM glicko_ratings;")
if [ "$RATING_COUNT" -lt 9 ]; then
    echo "WARNING: Missing rating categories (expected 9, found $RATING_COUNT)"
fi

echo "Health check completed successfully"
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Backup database
cp gw2_comprehensive.db "$BACKUP_DIR/gw2_leaderboard_$DATE.db"

# Backup configuration
cp sync_config.json "$BACKUP_DIR/sync_config_$DATE.json"

# Compress old backups
find "$BACKUP_DIR" -name "*.db" -mtime +7 -exec gzip {} \;

# Clean up very old backups
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR/gw2_leaderboard_$DATE.db"
```

### Log Monitoring

```bash
#!/bin/bash
# monitor_logs.sh

# Check for error patterns in output
if python sync_logs.py --check-only 2>&1 | grep -q "ERROR\|FAILED\|Exception"; then
    echo "Sync errors detected"
    python sync_logs.py --check-only 2>&1 | tail -20
fi

# Check disk space
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "WARNING: Disk usage at ${DISK_USAGE}%"
fi

# Check log file sizes
find extracted_logs/ -name "*.json" -size +10M -exec ls -lh {} \;
```

Run these scripts via cron for proactive monitoring:

```bash
# Add to crontab
0 6 * * * /path/to/health_check.sh >> /path/to/health.log 2>&1
0 2 * * * /path/to/backup.sh >> /path/to/backup.log 2>&1
*/30 * * * * /path/to/monitor_logs.sh >> /path/to/monitor.log 2>&1
```