# Getting Started with GW2 WvW Leaderboards

This guide will help you set up the GW2 WvW Leaderboard system from scratch and get your first leaderboards generated with all current features.

## Prerequisites

### System Requirements
- **Python 3.7 or higher**
- **Git** (for cloning the repository)
- **Web browser** (for viewing leaderboards)
- **Internet connection** (for automated log sync and guild integration)

### Required Python Libraries
```bash
# Install required dependencies
pip install requests beautifulsoup4

# The system also uses standard Python libraries:
# sqlite3, json, pathlib, datetime, re, concurrent.futures, etc. (all built-in)
```

### Optional: GW2 API Key
For guild features, you'll need a GW2 API key with appropriate permissions:
1. Go to https://account.arena.net/applications
2. Create a new key with these permissions: `account`, `guilds`
3. Save the API key for configuration later

### Installation

```bash
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

The system will automatically create all necessary database tables and add missing columns if needed.

## Step 3: Calculate Glicko-2 Ratings

Once your performance data is loaded, calculate skill ratings:

```bash
# Calculate all Glicko-2 ratings
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

This process analyzes each combat session and calculates pure Glicko-2 skill ratings for all 11 metrics.

## Step 4: Configure Guild Integration (Optional)

If you want guild member filtering and tracking:

### Edit sync_config.json
```json
{
  "log_aggregate_url": "https://pyrogw2.github.io",
  "database_path": "gw2_comprehensive.db",
  "extracted_logs_dir": "extracted_logs",
  "web_ui_output": "web_ui_output",
  "auto_confirm": false,
  "max_logs_per_run": 5,
  "guild_enabled": true,
  "guild_api_key": "YOUR_GW2_API_KEY_HERE",
  "guild_id": "YOUR_GUILD_ID_HERE",
  "guild_name": "Your Guild Name",
  "guild_tag": "TAG"
}
```

### Test Guild Integration
```bash
# Test guild member fetching
python guild_manager.py

# Check guild data in database
sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM guild_members;"
```

## Step 5: Generate Your First Leaderboards

Create the web interface with all current features:

```bash
# Generate web UI with full feature set
python generate_web_ui.py gw2_comprehensive.db -o web_ui_output
```

**Expected Output:**
```
Recalculating all Glicko ratings...
Rating recalculation complete!

Generating leaderboard data with up to 4 workers...
Processing 4 filters (overall first, then date-filtered)...
🚀 Processing 'overall' filter (fast)...
  Processing 11 individual metrics in parallel...
  Processing profession leaderboards in parallel...
  Processing high scores...
✅ Overall filter completed
🔄 Processing 3 date filters with ProcessPoolExecutor...
✅ All filters completed

Generating HTML UI...
HTML UI generated in: web_ui_output
Files created:
  - index.html
  - styles.css  
  - script.js

✅ Web UI generation complete!
📁 Output directory: web_ui_output
🌐 Open web_ui_output/index.html in your browser to view
```

## Step 6: View Your Leaderboards

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
- **Individual metric leaderboards** (DPS, Healing, etc.) - 11 total metrics
- **High Scores leaderboards** with record-breaking performances
- **Profession-specific rankings** with weighted combinations
- **Interactive player modals** - click any player name for detailed analysis
- **Date filtering options** (All Time, 30d, 90d, 180d)
- **Guild member filtering** (if configured)
- **Dark mode toggle** and responsive design

## Step 7: Set Up Automated Sync (Optional)

For ongoing automation, configure the sync system:

### Test Automated Sync
```bash
# Check for new logs
python sync_logs.py --check-only

# Download and process new logs (with confirmation)
python sync_logs.py

# Fully automated processing
python sync_logs.py --auto-confirm
```

### Configure for Full Automation
Edit `sync_config.json`:
```json
{
  "auto_confirm": true,
  "max_logs_per_run": 10,
  "guild_enabled": true
}
```

## Verification Checklist

After setup, verify everything is working:

- [ ] **Database exists**: `gw2_comprehensive.db` file created
- [ ] **Data loaded**: Check with `sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"`
- [ ] **Ratings calculated**: Check with `sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM glicko_ratings;"`
- [ ] **Guild integration**: Check with `sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM guild_members;"` (if enabled)
- [ ] **Web UI generated**: `web_ui_output/index.html` exists and loads
- [ ] **All leaderboards populated**: Can see player rankings in individual metrics, high scores, and professions
- [ ] **Player modals work**: Clicking player names opens detailed analysis
- [ ] **Date filtering works**: Different time periods show different results
- [ ] **Guild filtering works**: Can toggle between all players and guild members (if enabled)
- [ ] **Dark mode works**: Theme toggle functions properly
- [ ] **Sync configured**: `sync_config.json` exists with correct settings

## Common Setup Issues

### "No such column" Errors
If you see database column errors:
```bash
# The system should automatically add missing columns, but if issues persist:
rm gw2_comprehensive.db
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db
```

### Empty Leaderboards
If leaderboards show "No data available":
1. Verify logs were parsed: `sqlite3 gw2_comprehensive.db "SELECT COUNT(*) FROM player_performances;"`
2. Recalculate ratings: `python glicko_rating_system.py gw2_comprehensive.db --recalculate`
3. Regenerate UI: `python generate_web_ui.py gw2_comprehensive.db -o web_ui_output`

### Guild Integration Issues
If guild features aren't working:
1. Verify API key permissions at https://account.arena.net/applications
2. Check API key in `sync_config.json` has `account` and `guilds` permissions
3. Test: `python guild_manager.py`

### Sync Not Finding Logs
If automated sync finds no logs:
1. Check the URL in `sync_config.json`
2. Verify the site is accessible: `curl -s https://pyrogw2.github.io | head -20`
3. Try manual log placement in `extracted_logs/`

### Missing Python Libraries
```bash
# Install required dependencies
pip install requests beautifulsoup4

# On some systems, use pip3
pip3 install requests beautifulsoup4
```

### Player Modals Not Working
If clicking player names doesn't open modals:
1. Check browser console for JavaScript errors (F12)
2. Verify the web UI was generated completely
3. Regenerate: `python generate_web_ui.py gw2_comprehensive.db -o web_ui_output`

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
├── sync_config.json               # Sync and guild configuration
├── parse_logs_enhanced.py         # Core scripts
├── glicko_rating_system.py
├── generate_web_ui.py
├── sync_logs.py
├── guild_manager.py               # Guild integration
├── player_summary.py              # Player analysis
└── README.md
```

## Next Steps

Once your system is set up:

1. **Regular Updates**: Use `sync_logs.py --auto-confirm` to check for and process new logs
2. **Guild Management**: Monitor guild member changes and update API permissions as needed
3. **Customize**: Modify profession weightings and add new metrics as the game evolves
4. **Deploy**: Upload the web UI to GitHub Pages, Netlify, or your web server
5. **Monitor**: Check database size and performance as your log collection grows
6. **Explore**: Click on player names to explore the detailed performance analysis

See [DAILY_USAGE.md](DAILY_USAGE.md) for routine operation instructions and [CONFIGURATION.md](CONFIGURATION.md) for advanced customization options.

## Feature Highlights

Your system now includes:
- **11 comprehensive metrics** tracking all aspects of WvW performance
- **High scores system** for celebrating exceptional individual performances
- **Interactive player analysis** with detailed breakdowns by profession
- **Guild integration** with GW2 API for member tracking and filtering
- **Pure Glicko-2 ratings** without artificial composite scoring
- **Modern web interface** with dark mode and responsive design
- **Advanced automation** for hands-off operation