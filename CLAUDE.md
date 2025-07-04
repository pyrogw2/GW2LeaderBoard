# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Core Processing Pipeline
```bash
# RECOMMENDED: Complete automated workflow
python workflow.py --latest-only --auto-confirm

# Alternative: Manual steps
python sync_logs.py --auto-confirm
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db
python glicko_rating_system.py gw2_comprehensive.db --incremental
python generate_web_ui.py gw2_comprehensive.db -o web_ui_output

# Workflow script options
python workflow.py --ui-only           # Just regenerate UI
python workflow.py --parse-only        # Just parse logs
python workflow.py --force-rebuild     # Rebuild rating history
```

### Development and Testing
```bash
# Test log parsing on specific directory
python parse_logs_enhanced.py extracted_logs/YYYYMMDDHHMM/ -d test.db

# Analyze performance trends
python analyze_performance.py gw2_comprehensive.db

# Debug log parsing issues
python debug_parse.py path/to/problematic/log.html

# Simple statistical analysis
python simple_analysis.py gw2_comprehensive.db
```

### Database Operations
```bash
# Recalculate all Glicko ratings
python glicko_rating_system.py gw2_comprehensive.db --recalculate

# Rebuild rating history for Latest Change feature
python glicko_rating_system.py gw2_comprehensive.db --rebuild-history

# Rating system with date filtering
python glicko_rating_system.py gw2_comprehensive.db --days 30

# Generate ratings for specific time periods
python glicko_rating_system.py gw2_comprehensive.db --days 90 --temp-suffix _90d
```

## Project Architecture

### Core Components
- **`workflow.py`**: Complete automation script handling full pipeline from logs to web UI
- **`sync_logs.py`**: Automated log discovery and processing pipeline
- **`parse_logs_enhanced.py`**: TiddlyWiki HTML parser with comprehensive metric extraction
- **`glicko_rating_system.py`**: Advanced Glicko-2 rating system with session-based z-score normalization
- **`generate_web_ui.py`**: Static web interface generator with parallel processing and Latest Change feature
- **`guild_manager.py`**: GW2 API integration for guild member filtering

### Data Flow
1. **Workflow Orchestration**: `workflow.py` manages complete automation pipeline
2. **Log Collection**: `sync_logs.py` fetches TiddlyWiki logs from aggregate sites
3. **Parsing**: `parse_logs_enhanced.py` extracts 10+ performance metrics per player/session
4. **Rating Calculation**: `glicko_rating_system.py` applies advanced statistical analysis with rating history
5. **UI Generation**: `generate_web_ui.py` creates interactive leaderboards with Latest Change feature
6. **Guild Filtering**: `guild_manager.py` applies guild-specific member filtering

### Database Schema
- **`player_performances`**: Raw session data with 12 metrics per player
- **`glicko_ratings`**: Calculated skill ratings by metric and profession
- **`player_rating_history`**: Chronological rating history for Latest Change feature
- **`guild_members`**: Cached GW2 API guild member data
- **Indexes**: Optimized for date filtering and metric queries

### Performance Metrics Tracked
1. **DPS** - Damage per second to players
2. **Healing** - Healing output per second
3. **Barrier** - Barrier generation per second
4. **Cleanses** - Condition removal per second
5. **Strips** - Boon removal per second
6. **Stability** - Stability generation per second
7. **Resistance** - Resistance generation per second
8. **Might** - Might generation per second
9. **Protection** - Protection generation per second
10. **Down Contribution** - Damage to downed players per second
11. **Burst Consistency** - Performance consistency metric
12. **Distance to Tag** - Average distance from commander

## Key Technologies

### Dependencies
- **External**: `requests`, `beautifulsoup4`
- **Standard Library**: `sqlite3`, `statistics`, `math`, `concurrent.futures`, `dataclasses`
- **Python Version**: 3.7+ (required for dataclasses and advanced typing)

### Data Formats
- **Input**: TiddlyWiki HTML files with embedded JSON tiddlers
- **Storage**: SQLite database with normalized schema
- **Output**: Static HTML/CSS/JS web interface
- **Config**: JSON configuration files

### Algorithms
- **Rating System**: Glicko-2 with session-based z-score normalization
- **Composite Scoring**: Weighted combination of Glicko rating and percentile rank
- **Performance Analysis**: Statistical analysis within combat sessions
- **Guild Integration**: GW2 API v2 for member validation
- **Latest Change**: Chronological rating history with delta calculations

### Modern UI Features
- **iOS-style Segmented Control**: Time period selection (All, 30d, 90d, 180d)
- **Material Design Chips**: Guild filter options with emoji icons
- **Modern Toggle Switch**: Latest Change feature with smooth animations
- **Responsive Design**: Mobile-optimized layout with touch-friendly controls
- **Color-Coded Deltas**: Green (+), Red (-), Gray (0) for rating changes

## Configuration

### Primary Config: `sync_config.json`
- **log_aggregate_url**: Source for TiddlyWiki logs
- **database_path**: SQLite database location
- **guild settings**: API key, guild ID, member filtering options
- **processing limits**: Max logs per run, auto-confirmation settings

### Key Settings
- Guild member filtering can be enabled/disabled
- Date-based filtering for different time periods (30d, 90d, 180d)
- Profession-specific metric weighting
- Automated vs manual processing modes

## Development Notes

### Performance Considerations
- Database uses indexes for efficient date filtering
- Parallel processing in web UI generation
- Temporary databases for isolated calculations
- Session-based analysis prevents memory issues with large datasets

### Error Handling
- Graceful degradation when logs are malformed
- Comprehensive input validation and sanitization
- Transaction-based database operations
- Recovery mechanisms for partial processing failures

### Testing Approach
- Use `debug_parse.py` for individual log troubleshooting
- Test with `test.db` for isolated development
- Verify output with `simple_analysis.py` for statistical validation
- Manual verification against known combat sessions

### Code Patterns
- Extensive use of `dataclasses` for type safety
- Context managers for resource handling
- Progress reporting in long-running operations
- Modular design with clear separation of concerns

### Documentation Standards
- **Always update documentation before committing** - Update API_REFERENCE.md, GLICKO_SYSTEM.md, and other relevant docs when adding new features
- Keep CLAUDE.md synchronized with new commands and capabilities
- Document database schema changes in API_REFERENCE.md
- Update metric lists in documentation when adding new performance metrics