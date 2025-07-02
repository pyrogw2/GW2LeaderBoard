# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Core Processing Pipeline
```bash
# Full automated processing of new logs
python sync_logs.py --auto-confirm

# Manual log processing
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db
python glicko_rating_system.py gw2_comprehensive.db --recalculate

# Generate web interface
python generate_web_ui.py gw2_comprehensive.db -o web_ui_output

# Guild-specific processing
python sync_logs.py --guild-only
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

# Rating system with date filtering
python glicko_rating_system.py gw2_comprehensive.db --days 30

# Generate ratings for specific time periods
python glicko_rating_system.py gw2_comprehensive.db --days 90 --temp-suffix _90d
```

## Project Architecture

### Core Components
- **`sync_logs.py`**: Automated log discovery and processing pipeline
- **`parse_logs_enhanced.py`**: TiddlyWiki HTML parser with comprehensive metric extraction
- **`glicko_rating_system.py`**: Advanced Glicko-2 rating system with session-based z-score normalization
- **`generate_web_ui.py`**: Static web interface generator with parallel processing
- **`guild_manager.py`**: GW2 API integration for guild member filtering

### Data Flow
1. **Log Collection**: `sync_logs.py` fetches TiddlyWiki logs from aggregate sites
2. **Parsing**: `parse_logs_enhanced.py` extracts 9 performance metrics per player/session
3. **Rating Calculation**: `glicko_rating_system.py` applies advanced statistical analysis
4. **UI Generation**: `generate_web_ui.py` creates interactive leaderboards
5. **Guild Filtering**: `guild_manager.py` applies guild-specific member filtering

### Database Schema
- **`player_performances`**: Raw session data with 9 metrics per player
- **`glicko_ratings`**: Calculated skill ratings by metric and profession
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
9. **Down Contribution** - Damage to downed players per second

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