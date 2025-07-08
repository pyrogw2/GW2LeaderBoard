# API and Database Reference

This document provides technical reference information for the database schema, data structures, and internal APIs used by the GW2 WvW Leaderboard system.

## Recent Updates

### Modular Web UI Architecture & Enhanced Features
- **Modular Refactoring**: Restructured `generate_web_ui.py` from monolithic 5,086-line file into focused modules:
  - `data_processing.py` (509 lines): Database queries and filtering
  - `parallel_processing.py` (359 lines): Concurrent processing and progress tracking
  - `file_generator.py` (93 lines): Orchestration and file generation
  - `templates/html_templates.py` (267 lines): HTML structure generation
  - `templates/css_styles.py` (1,189 lines): Modern CSS with dark mode support
  - `templates/javascript_ui.py` (1,256 lines): Interactive UI functionality
- **Context Window Optimization**: All files now under 25,000 tokens for effective Claude development
- **Simplified Profession Ratings**: Profession-specific ratings now use transparent weighted averages of individual metric Glicko ratings instead of complex session-based calculations
- **Transparent Calculations**: Firebrand = (Stability × 0.6) + (Resistance × 0.4), Chronomancer = (Stability × 0.35) + (Cleanses × 0.35) + (Resistance × 0.15) + (Healing × 0.1) + (Barrier × 0.05), etc.
- **Transition to Pure Glicko Ratings**: Simplified system using Glicko-2 ratings directly instead of composite scores
- **Interactive Rating History Charts**: Time-series visualization showing player rating progression over time
- **Smart Profession Filtering**: Charts filter by specific professions, removing confusing "All Professions" aggregation
- **Chart.js Integration**: Professional interactive charts with dark mode support and detailed tooltips
- **Top 300 Player Coverage**: Rating history data generated for top 300 players across all metrics
- **Improved Date Filters**: Updated from All/30d/90d/180d to All/30d/60d/90d for better granularity
- **Latest Change Toggle**: Shows rating changes since most recent combat session across all time filters
- **Enhanced UI Contrast**: Improved visibility for toggle switches and date filters in dark mode
- **Comprehensive Workflow**: New `workflow.py` script handles complete pipeline from log download to web UI generation

## Database Schema

The system uses SQLite with two main tables for storing performance and rating data.

### player_performances

Stores raw performance data from each combat session.

```sql
CREATE TABLE player_performances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,                    -- Session timestamp (YYYYMMDDHHMM)
    account_name TEXT NOT NULL,                 -- Player account name
    profession TEXT NOT NULL,                   -- Player profession/specialization
    fight_time REAL NOT NULL,                   -- Duration of combat participation (seconds, ≥300s after filtering)
    target_dps REAL DEFAULT 0.0,              -- Damage per second to enemy players
    healing_per_sec REAL DEFAULT 0.0,         -- Healing output per second
    barrier_per_sec REAL DEFAULT 0.0,         -- Barrier generation per second
    condition_cleanses_per_sec REAL DEFAULT 0.0, -- Condition removal per second
    boon_strips_per_sec REAL DEFAULT 0.0,     -- Boon removal per second
    stability_gen_per_sec REAL DEFAULT 0.0,   -- Stability generation per second
    resistance_gen_per_sec REAL DEFAULT 0.0,  -- Resistance generation per second
    might_gen_per_sec REAL DEFAULT 0.0,       -- Might generation per second
    down_contribution_per_sec REAL DEFAULT 0.0, -- Down contribution per second
    distance_from_tag_avg REAL DEFAULT 0.0,   -- Average distance from tag in game units
    parsed_date TEXT,                          -- Date in YYYY-MM-DD format for filtering
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Record creation time
);
```

#### Indexes

```sql
CREATE INDEX idx_timestamp ON player_performances(timestamp);
CREATE INDEX idx_parsed_date ON player_performances(parsed_date);
CREATE INDEX idx_account_profession ON player_performances(account_name, profession);
CREATE INDEX idx_account_name ON player_performances(account_name);
```

#### Sample Data

```sql
-- Example record
INSERT INTO player_performances VALUES (
    1,                              -- id
    '202506302308',                -- timestamp
    'Dextra.8162',                 -- account_name
    'Weaver',                      -- profession
    2439.4,                        -- fight_time
    2493.02,                       -- target_dps
    150.5,                         -- healing_per_sec
    0.0,                           -- barrier_per_sec
    0.3,                           -- condition_cleanses_per_sec
    0.1,                           -- boon_strips_per_sec
    2.1,                           -- stability_gen_per_sec
    0.2,                           -- resistance_gen_per_sec
    8.5,                           -- might_gen_per_sec
    117.13,                        -- down_contribution_per_sec
    245.7,                         -- distance_from_tag_avg
    '2025-06-30',                  -- parsed_date
    '2025-07-01 16:00:00'          -- created_at
);
```

### player_rating_history

Stores chronological rating history for each player/profession/metric combination, enabling delta calculations.

```sql
CREATE TABLE player_rating_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,             -- Player account name
    profession TEXT NOT NULL,               -- Player profession/specialization
    metric_category TEXT NOT NULL,          -- Performance metric (DPS, Healing, etc.)
    timestamp TEXT NOT NULL,                -- Session timestamp (YYYYMMDDHHMM)
    rating REAL NOT NULL,                   -- Glicko-2 rating at this timestamp
    rating_deviation REAL NOT NULL,        -- Rating uncertainty at this timestamp
    volatility REAL NOT NULL,              -- Expected rating fluctuation
    UNIQUE(account_name, profession, metric_category, timestamp)
);
```

#### Sample Data

```sql
-- Example records showing rating progression
INSERT INTO player_rating_history VALUES (
    1, 'Dextra.8162', 'Weaver', 'DPS', '202506302308', 1878.56, 85.2, 0.045
);
INSERT INTO player_rating_history VALUES (
    2, 'Dextra.8162', 'Weaver', 'DPS', '202507032317', 1884.22, 83.1, 0.044
);
-- Delta calculation: 1884.22 - 1878.56 = +5.66 rating change
```

### glicko_ratings

Stores calculated Glicko ratings for each player/profession/metric combination.

```sql
CREATE TABLE glicko_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,                 -- Player account name
    profession TEXT NOT NULL,                   -- Player profession/specialization
    metric_category TEXT NOT NULL,              -- Metric name (DPS, Healing, etc.)
    rating REAL NOT NULL,                       -- Glicko rating (skill level)
    rating_deviation REAL NOT NULL,             -- Rating uncertainty
    volatility REAL NOT NULL,                   -- Performance consistency
    games_played INTEGER NOT NULL,              -- Number of sessions rated
    average_rank REAL NOT NULL,                 -- Average percentile rank (0-100)
    average_stat_value REAL NOT NULL,           -- Average raw metric value
    -- composite_score column removed in favor of pure Glicko ratings
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Last calculation time
    UNIQUE(account_name, profession, metric_category)
);
```

#### Indexes

```sql
CREATE INDEX idx_metric_category ON glicko_ratings(metric_category);
CREATE INDEX idx_glicko_rating ON glicko_ratings(rating DESC);
CREATE INDEX idx_account_profession_rating ON glicko_ratings(account_name, profession);
```

#### Sample Data

```sql
-- Example record
INSERT INTO glicko_ratings VALUES (
    1,                              -- id
    'Dextra.8162',                 -- account_name
    'Weaver',                      -- profession
    'DPS',                         -- metric_category
    1971.06,                       -- rating
    85.2,                          -- rating_deviation
    0.045,                         -- volatility
    19,                            -- games_played
    9.95,                          -- average_rank
    2459.11,                       -- average_stat_value
    2046.30,                       -- composite_score
    '2025-07-01 16:15:00'          -- last_updated
);
```

## Data Quality and Filtering

### Fight Time Outlier Filtering

The system automatically filters out players with extremely short participation times to maintain data quality:

#### Filtering Rules
- **Hard Minimum**: Players with ≥ 300 seconds (5 minutes) are always included
- **Outlier Detection**: Players below 25% of median fight time are filtered
- **Threshold Safety**: Only applies when outliers represent < 20% of session participants
- **Purpose**: Removes brief profession swaps, disconnections, or late arrivals that don't reflect true performance

#### Implementation
```python
def filter_fight_time_outliers(performances):
    HARD_MINIMUM = 300.0  # Always keep players with >= 5 minutes
    
    # Calculate outlier threshold
    median_time = statistics.median([p.fight_time for p in performances])
    outlier_threshold = min(median_time * 0.25, HARD_MINIMUM)
    
    # Filter outliers if they represent < 20% of players
    outliers = [p for p in performances if p.fight_time < outlier_threshold]
    if len(outliers) / len(performances) < 0.2:
        return [p for p in performances if p.fight_time >= outlier_threshold]
    return performances
```

#### Examples
- **Filtered**: 32s Willbender (profession swap), 75s Guardian (disconnect)
- **Preserved**: 319s Guardian (late joiner), 474s Scrapper (mid-raid arrival)

## Data Structures

### PlayerPerformance

Python dataclass representing a single player's session performance.

```python
@dataclass
class PlayerPerformance:
    timestamp: str                              # Session timestamp
    account_name: str                           # Player account name  
    profession: str                             # Player profession/elite spec
    fight_time: float                           # Combat duration (seconds)
    target_dps: float = 0.0                    # Damage per second to enemies
    healing_per_sec: float = 0.0               # Healing output per second
    barrier_per_sec: float = 0.0               # Barrier generation per second
    condition_cleanses_per_sec: float = 0.0    # Condition removal per second
    boon_strips_per_sec: float = 0.0           # Boon removal per second
    stability_gen_per_sec: float = 0.0         # Stability generation per second
    resistance_gen_per_sec: float = 0.0        # Resistance generation per second
    might_gen_per_sec: float = 0.0             # Might generation per second
    down_contribution_per_sec: float = 0.0     # Down contribution per second
    distance_from_tag_avg: float = 0.0         # Average distance from tag (game units)
    parsed_date: str = ""                      # YYYY-MM-DD format
```

### GlickoRating

Python dataclass representing a calculated Glicko rating.

```python
@dataclass  
class GlickoRating:
    account_name: str                           # Player account name
    profession: str                             # Player profession
    metric_category: str                        # Metric being rated
    rating: float                               # Glicko rating (1200-1800+ typical)
    rating_deviation: float                     # Uncertainty (50-350)
    volatility: float                           # Consistency (0.03-0.1 typical)
    games_played: int                           # Number of sessions
    average_rank: float                         # Average percentile (0-100)
    average_stat_value: float                   # Average raw metric value
    composite_score: float                      # Final ranking score
```

## Internal APIs

### parse_logs_enhanced.py

#### Functions

##### `parse_log_directory(directory_path: str) -> List[PlayerPerformance]`

Parses all logs in a directory structure.

**Parameters:**
- `directory_path`: Path to directory containing timestamped log folders

**Returns:**
- List of PlayerPerformance objects

**Example:**
```python
performances = parse_log_directory("extracted_logs/")
print(f"Parsed {len(performances)} player performances")
```

##### `parse_offensive_table(table_data: List[List[str]]) -> List[Dict]`

Extracts performance data from TiddlyWiki offensive stats table.

**Parameters:**
- `table_data`: 2D array representing table rows and columns

**Returns:**
- List of dictionaries containing player performance data

##### `insert_performance_data(db_path: str, performances: List[PlayerPerformance])`

Inserts performance data into database.

**Parameters:**
- `db_path`: Path to SQLite database file
- `performances`: List of PlayerPerformance objects to insert

### glicko_rating_system.py

#### Functions

##### `recalculate_all_glicko_ratings(db_path: str) -> None`

Recalculates all Glicko ratings from scratch.

**Parameters:**
- `db_path`: Path to SQLite database file

**Side Effects:**
- Clears existing glicko_ratings table
- Processes all sessions in player_performances table
- Populates glicko_ratings table with new calculations

##### `calculate_z_scores(session_data: List[Dict], metric: str) -> Dict[str, float]`

Calculates z-scores for players in a session.

**Parameters:**
- `session_data`: List of player performance dictionaries
- `metric`: Name of metric to calculate z-scores for

**Returns:**
- Dictionary mapping account names to z-scores

##### `update_glicko_rating(rating: float, rd: float, volatility: float, z_score: float) -> Tuple[float, float, float]`

Updates a single Glicko rating based on performance.

**Parameters:**
- `rating`: Current Glicko rating
- `rd`: Current rating deviation
- `volatility`: Current volatility
- `z_score`: Performance z-score for this session

**Returns:**
- Tuple of (new_rating, new_rd, new_volatility)

### generate_web_ui.py

#### Functions

##### `get_glicko_leaderboard_data(db_path: str, metric_category: str = None, limit: int = 500, date_filter: str = None) -> List[Tuple]`

Retrieves leaderboard data from database.

**Parameters:**
- `db_path`: Path to SQLite database file
- `metric_category`: Specific metric to filter by (optional)
- `limit`: Maximum number of results to return
- `date_filter`: Time period filter ('30d', '60d', '90d', or None)

**Returns:**
- List of tuples containing ranking data

##### `generate_html_ui(leaderboard_data: Dict, output_dir: str) -> None`

Generates complete web interface.

**Parameters:**
- `leaderboard_data`: Dictionary containing all leaderboard data
- `output_dir`: Directory to write HTML/CSS/JS files

**Side Effects:**
- Creates HTML, CSS, and JavaScript files
- Copies any necessary assets

### sync_logs.py

#### Functions

##### `fetch_available_logs(base_url: str) -> List[Dict]`

Fetches list of available logs from aggregate site.

**Parameters:**
- `base_url`: Base URL of the TiddlyWiki aggregate site

**Returns:**
- List of dictionaries describing available logs

##### `download_and_extract_log(log_info: Dict, extracted_logs_dir: str) -> bool`

Downloads and extracts a single log.

**Parameters:**
- `log_info`: Dictionary containing log metadata
- `extracted_logs_dir`: Directory to extract log data to

**Returns:**
- Boolean indicating success/failure

## Query Examples

### Common Database Queries

#### Get Recent Performance Data

```sql
-- Player performances in last 30 days
SELECT account_name, profession, AVG(target_dps) as avg_dps
FROM player_performances 
WHERE parsed_date >= date('now', '-30 days')
GROUP BY account_name, profession
ORDER BY avg_dps DESC
LIMIT 20;
```

#### Top Performers by Metric

```sql
-- Top DPS players (current ratings)
SELECT account_name, profession, rating, games_played
FROM glicko_ratings 
WHERE metric_category = 'DPS'
ORDER BY composite_score DESC
LIMIT 10;
```

#### Session Statistics

```sql
-- Session participation statistics
SELECT 
    timestamp,
    COUNT(*) as player_count,
    AVG(target_dps) as avg_dps,
    MAX(target_dps) as max_dps
FROM player_performances
GROUP BY timestamp
ORDER BY timestamp DESC
LIMIT 20;
```

#### Profession Distribution

```sql
-- Most popular professions
SELECT 
    profession,
    COUNT(DISTINCT account_name) as unique_players,
    COUNT(*) as total_sessions,
    AVG(target_dps) as avg_dps
FROM player_performances
GROUP BY profession
ORDER BY unique_players DESC;
```

#### Player Progression

```sql
-- Player improvement over time
SELECT 
    account_name,
    profession,
    date(substr(timestamp, 1, 4) || '-' || substr(timestamp, 5, 2) || '-' || substr(timestamp, 7, 2)) as session_date,
    AVG(target_dps) as daily_avg_dps
FROM player_performances
WHERE account_name = 'Dextra.8162'
GROUP BY account_name, profession, session_date
ORDER BY session_date;
```

### Data Export Queries

#### Complete Player Statistics

```sql
-- Full player statistics export
SELECT 
    p.account_name,
    p.profession,
    COUNT(*) as sessions,
    AVG(p.target_dps) as avg_dps,
    MAX(p.target_dps) as max_dps,
    AVG(p.healing_per_sec) as avg_healing,
    AVG(p.down_contribution_per_sec) as avg_down_contrib,
    g.rating as glicko_rating,
    g.composite_score
FROM player_performances p
LEFT JOIN glicko_ratings g ON 
    p.account_name = g.account_name AND 
    p.profession = g.profession AND 
    g.metric_category = 'DPS'
GROUP BY p.account_name, p.profession
ORDER BY g.composite_score DESC NULLS LAST;
```

#### Leaderboard Export

```sql
-- Export top 500 for external use
SELECT 
    ROW_NUMBER() OVER (ORDER BY composite_score DESC) as rank,
    account_name,
    profession,
    rating,
    games_played,
    ROUND(average_rank, 2) as avg_rank_percent,
    ROUND(average_stat_value, 2) as avg_stat_value,
    ROUND(composite_score, 2) as composite_score
FROM glicko_ratings
WHERE metric_category = 'DPS'
ORDER BY composite_score DESC
LIMIT 500;
```

## Performance Considerations

### Database Optimization

- Use prepared statements for repeated queries
- Add indexes for commonly filtered columns
- Use LIMIT clauses for large result sets
- Consider pagination for web interfaces

### Memory Management

- Process large datasets in batches
- Use database cursors instead of loading all data
- Clear Python objects after processing
- Monitor memory usage during rating calculations

### Scaling Guidelines

- **Small Scale** (< 1000 sessions): Current implementation works well
- **Medium Scale** (1000-10000 sessions): Add more indexes, consider batch processing
- **Large Scale** (> 10000 sessions): Consider database partitioning, incremental updates

## Rating History Charts

### Overview

The rating history chart system provides interactive time-series visualizations showing how player ratings evolve over time. Charts are integrated into player detail modals and support profession-specific filtering.

### Technical Implementation

#### Backend Data Generation

```python
# Core function for retrieving player rating history
def get_player_rating_history(db_path: str, account_name: str, profession: str = None, limit_months: int = 6):
    """
    Returns structured history data:
    {
        'metrics': {
            'DPS': [{'timestamp': 'YYYYMMDDHHMM', 'rating': float, 'profession': str, ...}, ...],
            'Healing': [...],
            ...
        },
        'professions': ['Weaver', 'Catalyst', ...],
        'date_range': {'start': 'YYYYMMDDHHMM', 'end': 'YYYYMMDDHHMM'}
    }
    """
```

#### Player Selection Strategy

Rating history is generated for the top 300 players using a ranking-based priority system:

```python
# Prioritize top-ranked players across all metrics
player_rankings = {}
for metric_data in data["date_filters"]["overall"]["individual_metrics"].values():
    for player in metric_data[:300]:  # Top 300 per metric
        player_name = player["account_name"]
        current_rank = player.get("rank", 999)
        if player_name not in player_rankings or current_rank < player_rankings[player_name]:
            player_rankings[player_name] = current_rank

# Sort by best ranking and take top 300
top_players = sorted(player_rankings.items(), key=lambda x: x[1])[:300]
```

#### Frontend Chart Integration

```javascript
// Chart initialization with Chart.js
function initializeRatingHistoryChart(accountName) {
    // Populate profession filter (no "All Professions" option)
    const professionSelect = document.getElementById('history-profession-select');
    playerHistory.professions.forEach(profession => {
        professionSelect.innerHTML += `<option value="${profession}">${profession}</option>`;
    });
    
    // Smart metric change handling
    document.getElementById('history-metric-select').addEventListener('change', () => {
        const selectedMetric = document.getElementById('history-metric-select').value;
        const availableProfessions = [...new Set(playerHistory.metrics[selectedMetric].map(point => point.profession))];
        if (availableProfessions.length > 0) {
            professionSelect.value = availableProfessions[0]; // Auto-select relevant profession
        }
        updateRatingChart(accountName);
    });
}
```

### Chart Features

#### Interactive Elements
- **Metric Selection**: DPS, Healing, Barrier, Cleanses, Strips, Stability, Resistance, Might, Protection, Downs, Distance to Tag
- **Profession Filtering**: Only shows professions the player has actually used for the selected metric
- **Dark Mode Support**: Automatic theme detection with appropriate colors and styling
- **Interactive Tooltips**: Show detailed rating information including rating deviation and volatility

#### Visual Design
- **Line Charts**: Clean time-series progression with smooth curves
- **Color Scheme**: Professional blue (#667eea) with transparency fills
- **Responsive Layout**: Adapts to modal container constraints
- **Grid Lines**: Subtle grid with theme-appropriate colors

#### Data Presentation
- **Time Range**: Last 6 months of rating history (configurable)
- **Data Points**: Individual session ratings with timestamps
- **Profession Context**: Each data point includes profession information
- **Status Messages**: Clear feedback when no data is available

### Database Integration

Rating history charts leverage the existing `player_rating_history` table structure:

```sql
-- Query example for chart data
SELECT profession, metric_category, timestamp, rating, rating_deviation, volatility
FROM player_rating_history
WHERE account_name = ? AND timestamp >= ?
ORDER BY timestamp ASC;
```

### Performance Considerations

- **Data Limiting**: Only top 300 players to balance coverage with performance
- **Time Filtering**: 6-month limit reduces data transfer and processing overhead
- **Profession Filtering**: Client-side filtering provides responsive interaction
- **Chart Destruction**: Proper Chart.js lifecycle management prevents memory leaks

### User Experience Design

#### Smart Defaults
- **Initial Profession**: First profession with data for selected metric
- **Metric Switching**: Automatically selects most relevant profession when changing metrics
- **No Aggregation**: Removed confusing "All Professions" option that mixed different roles

#### Error Handling
- **No Data Messages**: Clear feedback when player lacks rating history
- **Metric Availability**: Graceful handling when selected metric has no data for profession
- **Loading States**: Appropriate status messages during chart initialization

This chart system provides players with valuable insights into their performance progression while maintaining clean, focused visualizations appropriate for each profession's role.

## Date Filtering System

### Overview

The leaderboard supports multiple time period filters to allow analysis of performance across different timeframes. The system processes data for each filter independently to provide accurate comparisons.

### Available Time Filters

#### Filter Options
- **All Time**: Complete historical data from all sessions
- **30 Days**: Recent performance (last month)
- **60 Days**: Short-term trends (last 2 months) 
- **90 Days**: Medium-term analysis (last 3 months)

#### Filter Design Rationale
The current filter set provides optimal granularity for performance analysis:

- **30d**: Captures very recent performance and immediate improvements
- **60d**: Sweet spot for analyzing recent trends without excessive historical noise
- **90d**: Provides medium-term perspective for understanding longer performance patterns
- **All**: Complete historical context for overall player development

### Technical Implementation

#### Backend Processing
Each date filter creates a temporary database with recalculated ratings:

```python
date_filters = ['overall', '30d', '60d', '90d']

# Process each filter independently
for filter_name in date_filters:
    if filter_name == 'overall':
        # Use main database with pre-calculated ratings
        working_db_path = db_path
    else:
        # Create temporary database with date-filtered data
        working_db_path = calculate_date_filtered_ratings(db_path, filter_name)
        # Recalculate all ratings on filtered dataset
```

#### Frontend Implementation
Date filters are implemented as segmented controls for intuitive switching:

```html
<div class="segmented-control">
    <input type="radio" name="time-filter" id="time-all" value="overall" checked>
    <label for="time-all">All</label>
    <input type="radio" name="time-filter" id="time-30" value="30d">
    <label for="time-30">30d</label>
    <input type="radio" name="time-filter" id="time-60" value="60d">
    <label for="time-60">60d</label>
    <input type="radio" name="time-filter" id="time-90" value="90d">
    <label for="time-90">90d</label>
</div>
```

#### Database Date Filtering
The system uses the `parsed_date` column for efficient date-based queries:

```sql
-- Example: 60-day filter query
SELECT * FROM player_performances 
WHERE parsed_date >= date('now', '-60 days')
ORDER BY timestamp DESC;
```

### Performance Considerations

#### Processing Optimization
- **Parallel Processing**: Multiple date filters processed concurrently using process pools
- **Temporary Databases**: Isolated calculations prevent interference between filters
- **Guild Data Copying**: Member information propagated to temporary databases for consistent filtering

#### Memory Management
- **Automatic Cleanup**: Temporary databases removed after processing
- **Process Isolation**: Each filter runs in separate process to avoid memory accumulation
- **Batch Processing**: Large datasets processed in chunks to prevent memory exhaustion

### User Experience

#### Filter Switching
- **Instant Response**: Pre-calculated data enables immediate filter switching
- **Consistent Layout**: All filters maintain identical table structure and formatting
- **State Preservation**: Current metric and sorting preferences maintained across filter changes

#### Data Consistency
- **Independent Calculations**: Each filter recalculates ratings on its specific dataset
- **Relative Rankings**: Rankings reflect performance within the selected time period
- **Fair Comparisons**: Only sessions within the filter period contribute to ratings

This filtering system enables users to analyze performance trends across multiple timeframes while maintaining statistical accuracy and providing responsive user interaction.

## Rating System Evolution

### Pure Glicko Rating Implementation

As of the latest update, the leaderboard system has transitioned from composite scoring to pure Glicko-2 ratings for enhanced statistical accuracy and simplified interpretation.

#### Previous System (Composite Scoring)
The original system combined multiple factors:
- Glicko-2 rating (50% weight)
- Percentile rank performance (50% weight)  
- Participation bonus (0-10%)
- Experience scaling factors

#### Current System (Pure Glicko)
The simplified system uses Glicko-2 ratings directly:
- **Pure statistical approach**: Ratings based solely on performance outcomes
- **Uncertainty handling**: Proper accounting for rating deviation with small sample sizes
- **Simplified interpretation**: Higher rating = better skill level, period
- **Statistical soundness**: Standard Glicko-2 implementation without artificial modifications

#### Technical Implementation

##### Database Changes
```sql
-- Queries now sort by rating instead of composite_score
SELECT account_name, profession, rating, games_played
FROM glicko_ratings 
WHERE metric_category = 'DPS'
ORDER BY rating DESC  -- Changed from composite_score DESC
LIMIT 500;
```

##### Frontend Data Structure
```javascript
// Data structure now uses rating as the primary score
{
    "rank": 1,
    "account_name": "Player.1234",
    "profession": "Weaver",
    "composite_score": 1884.2,  // Now equals glicko_rating
    "glicko_rating": 1884.2,    // Primary sorting field
    "games_played": 20,
    "average_rank_percent": 4.35,
    "average_stat_value": 2505.6,
    "is_guild_member": true,
    "rating_delta": 5.66
}
```

##### Backward Compatibility
- **Composite scores preserved**: Database still contains composite_score column
- **Data structure maintained**: Frontend still references composite_score for compatibility
- **Migration path**: Easy rollback if needed by changing sort order back
- **Historical data intact**: No data loss during transition

#### Benefits of Pure Glicko System

##### Statistical Accuracy
- **Proper uncertainty handling**: Players with few games have appropriate rating deviation
- **Standard implementation**: Follows established Glicko-2 mathematical model
- **No artificial boosters**: Eliminates participation bonuses that could skew rankings
- **Fair comparisons**: All players evaluated using same statistical framework

##### Simplicity
- **Clear interpretation**: Rating directly reflects skill level
- **Reduced complexity**: No need to explain composite scoring components
- **Easier debugging**: Single rating source makes troubleshooting simpler
- **Standard range**: Typical 1200-1800+ range familiar to rating system users

##### System Performance
- **Faster queries**: Single column sorting instead of calculated composites
- **Cleaner code**: Reduced complexity in ranking algorithms
- **Better maintenance**: Standard Glicko-2 implementation easier to validate
- **Future improvements**: Easier to implement Glicko-2 enhancements

#### Migration Results

Analysis of top 20 DPS players showed minimal ranking disruption:
- **Top 3 unchanged**: Dextra.8162, Aein.1483, synco.8132 maintain positions
- **Minor adjustments**: Only 3-4 meaningful position changes in top 20
- **Statistical improvement**: Better handling of players with limited game history
- **User experience**: Rankings feel more intuitive and statistically sound

This transition maintains all existing functionality while providing a more accurate and interpretable rating system.

This reference provides the technical foundation for extending and maintaining the leaderboard system.