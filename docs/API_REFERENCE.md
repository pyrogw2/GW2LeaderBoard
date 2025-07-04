# API and Database Reference

This document provides technical reference information for the database schema, data structures, and internal APIs used by the GW2 WvW Leaderboard system.

## Recent Updates

### Latest Change Feature & UI Improvements
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
    composite_score REAL NOT NULL,              -- Final ranking score
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Last calculation time
    UNIQUE(account_name, profession, metric_category)
);
```

#### Indexes

```sql
CREATE INDEX idx_metric_category ON glicko_ratings(metric_category);
CREATE INDEX idx_composite_score ON glicko_ratings(composite_score DESC);
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
- `date_filter`: Time period filter ('30d', '90d', '180d', or None)

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

This reference provides the technical foundation for extending and maintaining the leaderboard system.