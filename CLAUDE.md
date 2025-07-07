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
- **`generate_web_ui.py`**: Modular web interface generator with orchestration and entry point
- **`guild_manager.py`**: GW2 API integration for guild member filtering

### Web UI Modular Structure (src/gw2_leaderboard/web/)
- **`generate_web_ui.py`**: Clean entry point with argument parsing (126 lines)
- **`data_processing.py`**: Database operations and data filtering (509 lines)
- **`parallel_processing.py`**: Concurrent processing and progress tracking (359 lines)
- **`file_generator.py`**: Orchestration and file generation (93 lines)
- **`templates/`**: Separated UI template modules
  - **`html_templates.py`**: Complete HTML structure (267 lines)
  - **`css_styles.py`**: Modern CSS with dark mode support (1,189 lines)
  - **`javascript_ui.py`**: Interactive UI functionality (1,256 lines)

### Data Flow
1. **Workflow Orchestration**: `workflow.py` manages complete automation pipeline
2. **Log Collection**: `sync_logs.py` fetches TiddlyWiki logs from aggregate sites
3. **Parsing**: `parse_logs_enhanced.py` extracts 10+ performance metrics per player/session
4. **Rating Calculation**: `glicko_rating_system.py` applies advanced statistical analysis with rating history
5. **UI Generation**: Modular web UI system creates interactive leaderboards with Latest Change feature
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
13. **APM** - Actions Per Minute (total/no_auto format, e.g., "68.0/55.0")

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
- **Profession Ratings**: Simple weighted averages of individual metric Glicko ratings (e.g., Firebrand = Stability×0.6 + Resistance×0.4)
- **Performance Analysis**: Statistical analysis within combat sessions
- **Guild Integration**: GW2 API v2 for member validation
- **Latest Change**: Chronological rating history with delta calculations
- **Date Filtering**: All metrics including APM support consistent date-based filtering across time periods
  - **Fixed**: Profession leaderboards now properly respect date filters using SQL-level filtering approach
  - **Fixed**: Average rank calculations now show actual rank positions (1st, 2nd, 3rd) instead of percentiles  
  - **Fixed**: High scores now use correct `burst_damage_1s` field instead of `burst_consistency_1s`

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

## Recent Bug Fixes (July 2025)

### Critical Date Filtering Issues Resolved

#### 1. Profession Leaderboard Date Filtering
- **Issue**: Profession leaderboards showed identical data across all time periods (30d, 60d, 90d)
- **Root Cause**: Used pre-calculated ratings from `glicko_ratings` table which don't respect date filters
- **Solution**: Implemented `calculate_simple_profession_ratings_fast_filter()` function using SQL-level date filtering
- **Files Modified**: `src/gw2_leaderboard/web/parallel_processing.py`, `src/gw2_leaderboard/web/templates/javascript_ui.py`
- **Verification**: Each time period now shows different player counts, rankings, and rating values

#### 2. Average Rank Calculation Fix
- **Issue**: Average rank showed impossible values (21.3+ for max 50-player squads)
- **Root Cause**: Calculated percentile ranks instead of actual position ranks
- **Solution**: Changed SQL from `AVG(100.0 * player_rank / session_size)` to `AVG(player_rank)`
- **Files Modified**: `src/gw2_leaderboard/web/data_processing.py` (`calculate_glicko_ratings_for_date_filter()`)

#### 3. High Scores Database Field Fix
- **Issue**: High scores missing known records (e.g., Synco's 148k burst damage)
- **Root Cause**: Query used wrong database field `burst_consistency_1s` instead of `burst_damage_1s`
- **Solution**: Updated SQL query to use correct field mapping
- **Files Modified**: `src/gw2_leaderboard/web/data_processing.py`

#### 4. JavaScript Data Structure Compatibility
- **Issue**: Profession leaderboards showed empty after backend changes
- **Root Cause**: Backend changed from `'players'` to `'leaderboard'` key but JavaScript still expected `'players'`
- **Solution**: Updated JavaScript template to use `data.leaderboard` consistently
- **Files Modified**: `src/gw2_leaderboard/web/templates/javascript_ui.py`

### Testing and Validation
All fixes have been verified to work correctly:
- Profession leaderboards show different data for each time period
- Average rank values are realistic (1-50 range for typical sessions)
- High scores display correct maximum values from database
- Web UI loads and displays profession data properly

### Development Guidelines

#### Code Organization and Maintainability
- **IMPORTANT: Keep all Python files under 25,000 tokens** to ensure they fit within Claude's context window for effective development and debugging
- **File Size Monitoring**: Use `wc -c filename.py` to check file sizes (aim for <100KB for most files)
- **Modular Design**: Break large files into focused, single-responsibility modules as demonstrated in the web UI refactoring
- **Current largest files**: `javascript_ui.py` (~1,256 lines), `css_styles.py` (~1,189 lines) - both well within limits

#### Module Structure Best Practices
- Use clear import patterns supporting both relative and absolute imports
- Separate concerns: templates, data processing, orchestration, and business logic
- Maintain backward compatibility when refactoring existing functionality
- Document module responsibilities and dependencies clearly

### Documentation Standards
- **Always update documentation before committing** - Update API_REFERENCE.md, GLICKO_SYSTEM.md, and other relevant docs when adding new features
- Keep CLAUDE.md synchronized with new commands and capabilities
- Document database schema changes in API_REFERENCE.md
- Update metric lists in documentation when adding new performance metrics

## Adding New Performance Metrics

This guide walks through the complete process of adding a new performance metric to the leaderboard system.

### 1. Database Schema (parse_logs_enhanced.py)

**Add field to PlayerPerformance dataclass:**
```python
@dataclass
class PlayerPerformance:
    # ... existing fields ...
    new_metric_value: float = 0.0  # Add your new metric field
```

**Update database schema in create_database():**
```python
def create_database(db_path: str):
    # ... existing schema ...
    new_metric_value REAL DEFAULT 0.0,  # Add to CREATE TABLE statement
```

### 2. Log Parsing (parse_logs_enhanced.py)

**Create parsing function for your metric:**
```python
def parse_new_metric_table(table_text: str) -> Dict[str, Dict]:
    """Parse your new metric from TiddlyWiki markup."""
    metric_stats = {}
    lines = table_text.split('\n')
    
    for line in lines:
        if line.startswith('|') and not line.startswith('|!'):
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            try:
                account_name = extract_tooltip(cells[1])  # Account from tooltip
                profession = extract_profession(cells[2])  # Profession from {{Class}}
                metric_value = extract_span_value(cells[X])  # Your metric from column X
                
                key = f"{account_name}_{profession}"
                metric_stats[key] = {
                    'account_name': account_name,
                    'profession': profession,
                    'new_metric_value': metric_value
                }
            except (ValueError, IndexError) as e:
                continue
    
    return metric_stats
```

**Integrate into parse_log_directory():**
```python
def parse_log_directory(log_dir: Path) -> List[PlayerPerformance]:
    # ... existing parsing ...
    
    # Read your new metric data
    new_metric_stats = {}
    new_metric_file = log_dir / f"{timestamp}-YourMetricFile.json"
    if new_metric_file.exists():
        with open(new_metric_file, 'r', encoding='utf-8') as f:
            new_metric_data = json.load(f)
        new_metric_stats = parse_new_metric_table(new_metric_data.get('text', ''))
    
    # Add to PlayerPerformance creation
    for player_data in players_data:
        # ... existing lookups ...
        new_metric_data = new_metric_stats.get(key, {})
        
        performance = PlayerPerformance(
            # ... existing fields ...
            new_metric_value=new_metric_data.get('new_metric_value', 0.0)
        )
```

**Update detect_build_variants() function:**
```python
def detect_build_variants(performances: List[PlayerPerformance]) -> List[PlayerPerformance]:
    # ... existing detection logic ...
    
    updated_performance = PlayerPerformance(
        # ... existing fields ...
        new_metric_value=performance.new_metric_value,  # Don't forget this!
    )
```

### 3. Database Storage (parse_logs_enhanced.py)

**Update store_performances() function:**
```python
def store_performances(cursor, performances: List[PlayerPerformance]):
    # Update INSERT statement to include new field
    cursor.execute('''
        INSERT OR REPLACE INTO player_performances VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    ''', (
        # ... existing fields ...
        perf.new_metric_value,  # Add to tuple
    ))
```

### 4. Rating System (glicko_rating_system.py)

**Add metric to METRICS list:**
```python
METRICS = [
    # ... existing metrics ...
    'new_metric_value',  # Add your metric
]
```

### 5. Web UI Integration (generate_web_ui.py)

**Add to profession metrics (if applicable):**
```python
PROFESSION_METRICS = {
    'YourProfession': {
        'metrics': ['existing_metric', 'new_metric_value'],  # Add to relevant professions
        'weights': [0.6, 0.4],  # Add corresponding weight
        'key_stats_format': 'ExistingMetric:{} NewMetric:{}'
    }
}
```

**Add to leaderboard columns:**
```python
# In generate_web_ui.py, add to table columns configuration
{
    'key': 'new_metric_value',
    'label': 'New Metric',
    'type': 'number'  # or 'custom' with special formatting
}
```

**Add formatting (if custom display needed):**
```javascript
// In script.js formatCellValue function
case 'new_metric':
    return value !== null ? `<span class="stat-value">${value.toFixed(1)}</span>` : '<span class="stat-value">-</span>';
```

### 6. Documentation Updates

1. **Update CLAUDE.md** - Add metric to "Performance Metrics Tracked" section
2. **Update API_REFERENCE.md** - Document database schema changes
3. **Update metric descriptions** in web UI About section

### 7. Testing Checklist

- [ ] Parsing function extracts correct values from log files
- [ ] Database schema includes new field
- [ ] PlayerPerformance objects store the metric correctly
- [ ] detect_build_variants() preserves the metric data
- [ ] Glicko ratings calculate for the new metric
- [ ] Web UI displays the metric in appropriate leaderboards
- [ ] Date filtering works with the new metric
- [ ] Database migration handles existing data gracefully

### Example: APM Implementation

The APM (Actions Per Minute) metric implementation serves as a complete reference:

- **Data Source**: Skill usage files in format "total/no_auto" (e.g., "68/55")
- **Storage**: Two fields (`apm_total`, `apm_no_auto`) 
- **Display**: Combined format "68.0/55.0" in profession leaderboards
- **Files Modified**: `parse_logs_enhanced.py`, `generate_web_ui.py`, `script.js`, `glicko_rating_system.py`
- **Key Challenge**: Ensuring detect_build_variants() preserves the data
- **Date Filtering**: APM calculations now respect date filtering parameters for consistent time-based analysis

This reference implementation demonstrates the complete workflow for adding complex metrics with custom formatting.