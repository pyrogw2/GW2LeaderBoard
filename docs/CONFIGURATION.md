# Configuration Reference

This document describes all configuration options and settings for the GW2 WvW Leaderboard system.

## Sync Configuration (`sync_config.json`)

The main configuration file for automated log synchronization.

### File Location
- Default: `sync_config.json` in the project root
- Override with: `--config /path/to/config.json`

### Configuration Options

```json
{
  "log_aggregate_url": "https://pyrogw2.github.io",
  "database_path": "gw2_comprehensive.db",
  "extracted_logs_dir": "extracted_logs",
  "web_ui_output": "web_ui_final",
  "auto_confirm": false,
  "max_logs_per_run": 5
}
```

#### `log_aggregate_url`
- **Type**: String (URL)
- **Default**: `"https://pyrogw2.github.io"`
- **Description**: Base URL for the TiddlyWiki aggregate site containing combat logs
- **Examples**:
  - `"https://pyrogw2.github.io"`
  - `"https://your-guild.github.io/logs"`
  - `"http://localhost:8000/logs"`

#### `database_path`
- **Type**: String (file path)
- **Default**: `"gw2_comprehensive.db"`
- **Description**: Path to the SQLite database file (relative or absolute)
- **Examples**:
  - `"gw2_comprehensive.db"` (current directory)
  - `"data/leaderboards.db"` (subdirectory)
  - `"/var/lib/gw2/database.db"` (absolute path)

#### `extracted_logs_dir`
- **Type**: String (directory path)
- **Default**: `"extracted_logs"`
- **Description**: Directory where extracted log data is stored
- **Examples**:
  - `"extracted_logs"` (current directory)
  - `"logs/extracted"` (subdirectory)
  - `"/tmp/gw2_logs"` (temporary directory)

#### `web_ui_output`
- **Type**: String (directory path)
- **Default**: `"web_ui_final"`
- **Description**: Output directory for generated web interface
- **Examples**:
  - `"web_ui_final"` (current directory)
  - `"public_html"` (web server directory)
  - `"/var/www/leaderboards"` (system web directory)

#### `auto_confirm`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Skip user confirmation prompts during sync
- **Values**:
  - `true`: Automatically proceed with downloads and processing
  - `false`: Prompt user for confirmation before actions

#### `max_logs_per_run`
- **Type**: Integer
- **Default**: `5`
- **Description**: Maximum number of new logs to process in a single sync run
- **Range**: 1-50 (recommended)
- **Purpose**: Prevents overwhelming the system with too many logs at once

## Rating System Configuration

Configuration is embedded in `glicko_rating_system.py`. These settings require code changes and recalculation.

### Core Glicko Parameters

```python
# Rating system constants
INITIAL_RATING = 1500          # Starting rating for new players
INITIAL_RD = 350              # Initial rating deviation (uncertainty)
INITIAL_VOLATILITY = 0.06     # Initial volatility

# Glicko algorithm parameters  
CONVERGENCE_TOLERANCE = 0.000001  # Calculation precision
MAX_ITERATIONS = 100              # Safety limit for convergence
TAU = 0.5                        # Volatility control parameter
```

#### `INITIAL_RATING`
- **Type**: Integer
- **Default**: `1500`
- **Description**: Starting Glicko rating for new players
- **Range**: 1000-2000 (standard Glicko range)
- **Impact**: Higher values make new players start with higher perceived skill

#### `INITIAL_RD`
- **Type**: Integer  
- **Default**: `350`
- **Description**: Initial rating deviation (uncertainty)
- **Range**: 200-500
- **Impact**: Higher values make ratings change more quickly for new players

#### `INITIAL_VOLATILITY`
- **Type**: Float
- **Default**: `0.06`
- **Description**: Expected consistency of player performance
- **Range**: 0.03-0.1
- **Impact**: Higher values expect more erratic performance

#### `TAU`
- **Type**: Float
- **Default**: `0.5`
- **Description**: System constant controlling volatility change rate
- **Range**: 0.2-1.0
- **Impact**: Higher values allow volatility to change more quickly

### Session Requirements

```python
# Minimum requirements for session validity
MIN_PLAYERS_PER_SESSION = 5    # Minimum players for meaningful comparison
MIN_FIGHT_TIME = 30           # Minimum fight duration (seconds)
```

#### `MIN_PLAYERS_PER_SESSION`
- **Type**: Integer
- **Default**: `5`
- **Description**: Minimum number of players required for a session to be rated
- **Range**: 3-20
- **Impact**: Lower values include more sessions but may reduce rating accuracy

#### `MIN_FIGHT_TIME`
- **Type**: Integer
- **Default**: `30`
- **Description**: Minimum fight duration in seconds for valid performance data
- **Range**: 10-300
- **Impact**: Higher values exclude brief skirmishes but improve data quality

### Metric Categories

```python
METRIC_CATEGORIES = {
    'DPS': 'target_dps',
    'Healing': 'healing_per_sec',
    'Barrier': 'barrier_per_sec', 
    'Cleanses': 'condition_cleanses_per_sec',
    'Strips': 'boon_strips_per_sec',
    'Stability': 'stability_gen_per_sec',
    'Resistance': 'resistance_gen_per_sec',
    'Might': 'might_gen_per_sec',
    'Downs': 'down_contribution_per_sec'
}
```

**Structure**:
- **Key**: Display name for the metric
- **Value**: Database column name containing the per-second value

**Adding New Metrics**:
1. Add database column: `ALTER TABLE player_performances ADD COLUMN new_metric_per_sec REAL DEFAULT 0.0;`
2. Update parser to extract the metric
3. Add entry to `METRIC_CATEGORIES`
4. Update web UI to include the metric

### Profession-Specific Weights

```python
PROFESSION_METRICS = {
    'Firebrand': {
        'DPS': 0.3,
        'Healing': 0.25,
        'Barrier': 0.2,
        'Cleanses': 0.1,
        'Stability': 0.15
    },
    'Scourge': {
        'DPS': 0.4,
        'Cleanses': 0.3,
        'Strips': 0.2,
        'Barrier': 0.1
    },
    # ... other professions
}
```

**Requirements**:
- Weights must sum to 1.0 for each profession
- Only include metrics that are meaningful for the profession
- Weights reflect the profession's intended role

**Modifying Weights**:
1. Edit the values in `PROFESSION_METRICS`
2. Run: `python glicko_rating_system.py gw2_comprehensive.db --recalculate`
3. Regenerate UI: `python generate_web_ui.py gw2_comprehensive.db -o output_dir`

## Web UI Configuration

Configuration is in `generate_web_ui.py`. Changes require regenerating the UI.

### Individual Metrics

```python
individual_categories = [
    'DPS', 'Healing', 'Barrier', 'Cleanses', 
    'Strips', 'Stability', 'Resistance', 'Might', 'Downs'
]
```

Controls which metrics appear as individual leaderboard buttons.

### Profession List

```python
profession_buttons = [
    'Firebrand', 'Chronomancer', 'Scourge', 
    'Druid', 'Condi Firebrand', 'Support Spb'
]
```

Controls which professions have dedicated leaderboard pages.

### Profession Icons

```python
profession_icons = {
    'Firebrand': 'https://wiki.guildwars2.com/images/0/02/Firebrand_icon.png',
    'Chronomancer': 'https://wiki.guildwars2.com/images/8/8b/Chronomancer_icon.png',
    # ... other mappings
}
```

**Icon Requirements**:
- Must be accessible URLs or relative paths
- Recommended size: 16x16 to 32x32 pixels
- PNG format preferred for transparency

### Date Filter Options

```python
date_filters = ['overall', '30d', '90d', '180d']
```

Available time period filters. To add new periods:

1. Add to this list (e.g., `'7d'`, `'365d'`)
2. Update `parse_date_filter()` function to handle the new period
3. Update HTML template to include the new button

## Database Configuration

The SQLite database requires no external configuration, but you can optimize it:

### Performance Settings

```sql
-- Add these pragmas for better performance
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = MEMORY;
```

### Useful Indexes

```sql
-- Performance indexes (created automatically)
CREATE INDEX IF NOT EXISTS idx_timestamp ON player_performances(timestamp);
CREATE INDEX IF NOT EXISTS idx_parsed_date ON player_performances(parsed_date);
CREATE INDEX IF NOT EXISTS idx_account_profession ON player_performances(account_name, profession);
CREATE INDEX IF NOT EXISTS idx_metric_category ON glicko_ratings(metric_category);
```

## Parser Configuration

Configuration in `parse_logs_enhanced.py` for log processing behavior.

### Data Validation Limits

```python
# Maximum reasonable values (outlier detection)
MAX_DPS = 50000
MAX_HEALING = 20000  
MAX_BARRIER = 10000
MIN_FIGHT_TIME = 30
```

Adjust these based on game balance changes and observed maximums.

### Column Mapping

```python
# TiddlyWiki table column positions (0-indexed)
ACCOUNT_NAME_COLUMN = 1
PROFESSION_COLUMN = 2
FIGHT_TIME_COLUMN = 3
TOTAL_DAMAGE_COLUMN = 4
# ... other columns
DOWN_CONTRIBUTION_COLUMN = 21
```

Update these if the TiddlyWiki log format changes.

## Environment Variables

You can override some settings using environment variables:

### Database Path
```bash
export GW2_DATABASE_PATH="/path/to/database.db"
python generate_web_ui.py
```

### Debug Mode
```bash
export GW2_DEBUG=1
python parse_logs_enhanced.py extracted_logs/
```

### Sync URL Override
```bash
export GW2_SYNC_URL="https://alternative-site.com"
python sync_logs.py --check-only
```

## Deployment Configuration

### Static Web Hosting

For GitHub Pages deployment:

```yaml
# .github/workflows/deploy.yml
name: Deploy Leaderboards
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
env:
  DATABASE_PATH: 'gw2_comprehensive.db'
  OUTPUT_DIR: 'docs'  # GitHub Pages source
```

### Server Deployment

For dedicated server hosting:

```bash
# Production configuration
export GW2_DATABASE_PATH="/var/lib/gw2/leaderboards.db"
export GW2_WEB_OUTPUT="/var/www/html/leaderboards"
export GW2_LOG_LEVEL="INFO"

# Automated processing
*/30 * * * * cd /opt/gw2-leaderboards && python sync_logs.py --auto-confirm --max-logs 3
0 6 * * * cd /opt/gw2-leaderboards && python generate_web_ui.py "$GW2_DATABASE_PATH" -o "$GW2_WEB_OUTPUT"
```

### Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .
RUN pip install requests

# Configuration via environment
ENV GW2_DATABASE_PATH=/data/gw2_comprehensive.db
ENV GW2_WEB_OUTPUT=/app/public
ENV GW2_AUTO_CONFIRM=true

VOLUME ["/data", "/app/public"]
CMD ["python", "sync_logs.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  gw2-leaderboards:
    build: .
    volumes:
      - ./data:/data
      - ./public:/app/public
    environment:
      - GW2_SYNC_URL=https://pyrogw2.github.io
      - GW2_MAX_LOGS=5
    restart: unless-stopped
```

## Security Configuration

### File Permissions

```bash
# Secure file permissions
chmod 755 *.py                    # Scripts executable
chmod 644 sync_config.json        # Config readable
chmod 660 gw2_comprehensive.db    # Database read/write for user/group
chmod 755 extracted_logs/         # Directory accessible
chmod 644 extracted_logs/*/*.json # Log files readable
```

### Network Security

For restricted environments:

```python
# In sync_logs.py, add SSL verification and proxies
response = requests.get(
    url, 
    timeout=30,
    verify=True,  # SSL certificate verification
    proxies={
        'http': 'http://proxy.company.com:8080',
        'https': 'https://proxy.company.com:8080'
    }
)
```

### Data Sanitization

The system includes built-in protections:
- SQL injection prevention via parameterized queries
- HTML escaping in web output
- File path validation
- Input size limits

## Backup Configuration

### Automated Backups

```bash
#!/bin/bash
# backup_config.sh

BACKUP_RETENTION_DAYS=30
BACKUP_DIR="/backups/gw2-leaderboards"
DATABASE_PATH="gw2_comprehensive.db"

# Daily backup
cp "$DATABASE_PATH" "$BACKUP_DIR/gw2_$(date +%Y%m%d).db"

# Weekly configuration backup  
if [ $(date +%w) -eq 0 ]; then  # Sunday
    tar -czf "$BACKUP_DIR/config_$(date +%Y%m%d).tar.gz" \
        sync_config.json \
        *.py \
        docs/
fi

# Cleanup old backups
find "$BACKUP_DIR" -name "gw2_*.db" -mtime +$BACKUP_RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "config_*.tar.gz" -mtime +$((BACKUP_RETENTION_DAYS * 4)) -delete
```

### Restore Procedures

```bash
# Restore database
cp /backups/gw2-leaderboards/gw2_20250101.db gw2_comprehensive.db

# Restore configuration
tar -xzf /backups/gw2-leaderboards/config_20250101.tar.gz

# Verify restoration
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"
python generate_web_ui.py gw2_comprehensive.db -o test_restore
```

This configuration system provides flexibility while maintaining sensible defaults for most use cases.