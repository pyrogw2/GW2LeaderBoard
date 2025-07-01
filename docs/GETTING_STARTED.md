# Getting Started with GW2 WvW Leaderboards

This guide will help you set up the GW2 WvW Leaderboard system from scratch and get your first leaderboards generated.

## Prerequisites

### System Requirements
- **Python 3.7 or higher**
- **Git** (for cloning the repository)
- **Web browser** (for viewing leaderboards)
- **Internet connection** (for automated log sync)

### Required Python Libraries
The system uses only standard Python libraries:
- `sqlite3` (built-in)
- `json` (built-in)
- `requests` (install with `pip install requests`)
- `pathlib`, `datetime`, `re`, etc. (all built-in)

### Installation

```bash
# Install Python dependencies
pip install requests

# Clone the repository (if from Git)
git clone <repository-url>
cd GW2LeaderBoard

# Or download and extract the files to a directory
```

## Step 1: Prepare Your Combat Logs

The system works with TiddlyWiki-format combat logs. You have several options:

### Option A: Automated Sync (Recommended)
If your logs are hosted on a TiddlyWiki aggregate site like pyrogw2.github.io:

```bash
# Check what logs are available
python sync_logs.py --check-only
```

This will show you available logs and create a `sync_config.json` file.

### Option B: Manual Log Files
If you have TiddlyWiki HTML files:

1. Create an `extracted_logs` directory
2. For each log, create a subdirectory with the timestamp (YYYYMMDDHHMM format)
3. Place the log files in the appropriate subdirectories

Example structure:
```
extracted_logs/
├── 202506302308/
│   ├── 202506302308-Offensive.json
│   ├── 202506302308-DPS-Stats.json
│   └── ... (other log files)
└── 202506192306/
    ├── 202506192306-Offensive.json
    └── ...
```

### Option C: Extract from TiddlyWiki Files
If you have complete TiddlyWiki HTML files:

```bash
# Extract from a single TiddlyWiki file
python extract_logs.py logfile.html -o extracted_logs/

# Or let the parser handle it directly
python parse_logs_enhanced.py logfile.html -d gw2_comprehensive.db
```

## Step 2: Initialize the Database

Create your first database and parse your logs:

```bash
# Parse logs from directory (creates database if it doesn't exist)
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db

# Or parse a single TiddlyWiki file
python parse_logs_enhanced.py single_log.html -d gw2_comprehensive.db
```

**Expected Output:**
```
🔍 Scanning for logs in extracted_logs/...
📁 Found 31 log directories
📊 Processing log 1/31: 202504102316
✅ Processed 64 players from 202504102316
...
✅ Database updated successfully! Total records: 1,368
```

If you see errors about missing columns, the system will automatically add them.

## Step 3: Calculate Glicko Ratings

Once your performance data is loaded, calculate skill ratings:

```bash
# Calculate all Glicko ratings
python glicko_rating_system.py gw2_comprehensive.db --recalculate
```

**Expected Output:**
```
Recalculating all Glicko ratings...
Processing session 1/31: 202504102316
  Processing DPS Glicko ratings...
    Session stats: mean=803.5, std=831.1, players=64
...
Rating recalculation complete!
```

This process analyzes each combat session and calculates skill ratings for all metrics.

## Step 4: Generate Your First Leaderboards

Create the web interface:

```bash
# Generate web UI
python generate_web_ui.py gw2_comprehensive.db -o web_ui_output
```

**Expected Output:**
```
Generating leaderboard data...
Generating data for overall...
  Individual metric leaderboards...
    Processing DPS...
    Processing Healing...
    ...
✅ Web UI generation complete!
📁 Output directory: web_ui_output
🌐 Open web_ui_output/index.html in your browser to view
```

## Step 5: View Your Leaderboards

Open the generated web interface:

```bash
# On macOS
open web_ui_output/index.html

# On Linux
xdg-open web_ui_output/index.html

# On Windows
start web_ui_output/index.html

# Or manually open the file in your web browser
```

You should see:
- Individual metric leaderboards (DPS, Healing, etc.)
- Profession-specific rankings
- Date filtering options
- Interactive sorting and search

## Step 6: Set Up Automated Sync (Optional)

For ongoing automation, configure the sync system:

### Edit Configuration
Modify `sync_config.json` to match your needs:

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

### Test Automated Sync
```bash
# Check for new logs
python sync_logs.py --check-only

# Download and process new logs (with confirmation)
python sync_logs.py

# Fully automated processing
python sync_logs.py --auto-confirm
```

## Verification Checklist

After setup, verify everything is working:

- [ ] **Database exists**: `gw2_comprehensive.db` file created
- [ ] **Data loaded**: Check with `sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"`
- [ ] **Ratings calculated**: Check with `sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM glicko_ratings;"`
- [ ] **Web UI generated**: `web_ui_output/index.html` exists and loads
- [ ] **Leaderboards populated**: Can see player rankings in the web interface
- [ ] **Date filtering works**: Different time periods show different results
- [ ] **Sync configured**: `sync_config.json` exists with correct settings

## Common Setup Issues

### "No such column" Errors
If you see database column errors:
```bash
# Delete the database and re-parse
rm gw2_comprehensive.db
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db
```

### Empty Leaderboards
If leaderboards show "No data available":
1. Verify logs were parsed: `sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"`
2. Recalculate ratings: `python glicko_rating_system.py gw2_comprehensive.db --recalculate`
3. Regenerate UI: `python generate_web_ui.py gw2_comprehensive.db -o web_ui_output`

### Sync Not Finding Logs
If automated sync finds no logs:
1. Check the URL in `sync_config.json`
2. Verify the site is accessible
3. Try manual log placement in `extracted_logs/`

### Missing Python Libraries
```bash
# Install required dependencies
pip install requests

# On some systems, use pip3
pip3 install requests
```

## Directory Structure After Setup

Your directory should look like this:
```
GW2LeaderBoard/
├── docs/                          # Documentation
├── extracted_logs/                # Log data directories
│   ├── 202506302308/
│   └── ...
├── web_ui_output/                 # Generated web interface
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── gw2_comprehensive.db           # SQLite database
├── sync_config.json               # Sync configuration
├── parse_logs_enhanced.py         # Core scripts
├── glicko_rating_system.py
├── generate_web_ui.py
├── sync_logs.py
└── README.md
```

## Next Steps

Once your system is set up:

1. **Regular Updates**: Use `sync_logs.py` to check for and process new logs
2. **Customize**: Modify profession weightings and add new metrics as needed
3. **Deploy**: Upload the web UI to GitHub Pages, Netlify, or your web server
4. **Monitor**: Check database size and performance as your log collection grows

See [DAILY_USAGE.md](DAILY_USAGE.md) for routine operation instructions.