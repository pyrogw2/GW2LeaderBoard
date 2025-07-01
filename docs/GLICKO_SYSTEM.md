# Glicko Rating System Documentation

This document explains the rating system implementation, maintenance procedures, and how to extend it with new metrics and leaderboards.

## Glicko Rating System Overview

### What is Glicko?

The Glicko rating system is an advanced improvement over the traditional Elo rating system, designed by Mark Glickman. It addresses several limitations of Elo by incorporating:

1. **Rating Uncertainty (RD)**: How confident we are in a player's rating
2. **Volatility**: How erratic a player's performance has been
3. **Time Decay**: Ratings become less certain over time without games

### Why Glicko for WvW?

WvW combat has unique characteristics that make Glicko ideal:

- **Variable Skill Exposure**: Players don't fight each other directly like in 1v1 games
- **Session-Based Performance**: Combat happens in discrete sessions with different participants
- **Role Diversity**: Different professions have different performance expectations
- **Irregular Participation**: Players may have gaps between combat sessions

## Implementation Details

### Core Algorithm Components

#### 1. Session-Based Z-Score Calculation

For each combat session, we calculate how each player performed relative to others in that session:

```python
def calculate_z_scores(session_data, metric):
    values = [player[metric] for player in session_data if player[metric] > 0]
    if len(values) < 2:
        return {}
    
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 1.0
    if std == 0:
        std = 1.0
    
    z_scores = {}
    for player in session_data:
        if player[metric] > 0:
            z_scores[player['account_name']] = (player[metric] - mean) / std
    
    return z_scores
```

**Why Z-Scores?**
- Normalizes performance across sessions with different skill levels
- Accounts for varying group sizes and compositions
- Makes performance comparable across time periods

#### 2. Glicko Rating Updates

Each player's rating is updated based on their z-score performance:

```python
def update_glicko_rating(rating, rd, volatility, z_score, opponent_rating=1500, opponent_rd=350):
    # Glicko algorithm implementation
    # rating: current rating
    # rd: rating deviation (uncertainty)
    # volatility: how erratic the player's performance is
    # z_score: performance in this session
```

**Key Parameters:**
- **Initial Rating**: 1500 (standard Glicko starting point)
- **Initial RD**: 350 (high uncertainty for new players)
- **Initial Volatility**: 0.06 (moderate performance consistency expectation)

#### 3. Composite Score Calculation

The final ranking score combines multiple factors:

```python
composite_score = glicko_rating + (100 - average_rank_percent) * 10
```

**Components:**
- **Glicko Rating**: Base skill assessment (1200-1800+ range)
- **Average Rank Percent**: How often the player ranks in top percentiles
- **Scaling Factor**: 10x multiplier to balance the components

### Metric Categories

The system tracks 9 distinct performance metrics:

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

Each metric gets its own independent Glicko rating, allowing players to excel in different areas.

## Profession-Specific Rankings

### Weighted Metric System

Different professions are evaluated using weighted combinations of metrics:

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

**Design Principles:**
- Weights sum to 1.0 for each profession
- Reflect the intended role of each profession
- Balance offensive and defensive contributions
- Account for meta shifts over time

### Profession Rating Calculation

```python
def calculate_profession_rating(player_ratings, profession_weights):
    weighted_sum = 0
    total_weight = 0
    
    for metric, weight in profession_weights.items():
        if metric in player_ratings:
            weighted_sum += player_ratings[metric] * weight
            total_weight += weight
    
    if total_weight > 0:
        return weighted_sum / total_weight
    return 1500  # Default rating
```

## Maintenance Procedures

### Adding New Metrics

#### 1. Database Schema Update

Add new column to `player_performances` table:

```sql
ALTER TABLE player_performances ADD COLUMN new_metric_per_sec REAL DEFAULT 0.0;
```

#### 2. Parser Integration

Update `parse_logs_enhanced.py`:

```python
# Add to PlayerPerformance dataclass
@dataclass
class PlayerPerformance:
    # ... existing fields
    new_metric_per_sec: float = 0.0

# Add to extraction logic
def parse_offensive_table(table_data):
    # ... existing parsing
    new_metric_value = extract_column_value(row, NEW_METRIC_COLUMN_INDEX)
    new_metric_per_sec = new_metric_value / fight_time if fight_time > 0 else 0.0
```

#### 3. Rating System Integration

Update `glicko_rating_system.py`:

```python
METRIC_CATEGORIES = {
    # ... existing metrics
    'NewMetric': 'new_metric_per_sec'
}
```

#### 4. UI Integration

Update `generate_web_ui.py`:

```python
individual_categories = [
    # ... existing categories
    'NewMetric'
]

# Add button to HTML template
<button class="metric-button" data-metric="NewMetric">New Metric</button>
```

### Modifying Profession Weights

#### 1. Edit Configuration

Modify weights in `glicko_rating_system.py`:

```python
PROFESSION_METRICS = {
    'Firebrand': {
        'DPS': 0.25,        # Reduced from 0.3
        'Healing': 0.3,     # Increased from 0.25
        'Barrier': 0.2,
        'Cleanses': 0.1,
        'Stability': 0.15
    }
}
```

#### 2. Recalculate Ratings

```bash
python glicko_rating_system.py gw2_comprehensive.db --recalculate
python generate_web_ui.py gw2_comprehensive.db -o web_ui_final
```

**Note:** Weight changes affect all historical data, so consider the impact on existing rankings.

### Adding New Professions

#### 1. Define Metric Weights

Add to `PROFESSION_METRICS` in `glicko_rating_system.py`:

```python
PROFESSION_METRICS = {
    # ... existing professions
    'NewProfession': {
        'DPS': 0.4,
        'Healing': 0.2,
        'Barrier': 0.2,
        'Cleanses': 0.1,
        'Stability': 0.1
    }
}
```

#### 2. Update UI

Add profession button in `generate_web_ui.py`:

```python
profession_buttons = [
    # ... existing professions
    'NewProfession'
]
```

#### 3. Add Profession Icon

Update icon mapping:

```python
profession_icons = {
    # ... existing icons
    'NewProfession': 'https://wiki.guildwars2.com/images/...'
}
```

## Advanced Configuration

### Glicko Parameters Tuning

You can adjust the core Glicko parameters in `glicko_rating_system.py`:

```python
# Rating system constants
INITIAL_RATING = 1500      # Starting rating for new players
INITIAL_RD = 350          # Initial uncertainty (higher = more volatile)
INITIAL_VOLATILITY = 0.06  # Performance consistency expectation

# Glicko algorithm parameters
CONVERGENCE_TOLERANCE = 0.000001  # Precision of calculations
MAX_ITERATIONS = 100              # Safety limit for calculations
TAU = 0.5                        # System constant (volatility control)
```

**Parameter Effects:**
- **Higher INITIAL_RD**: New players' ratings change more quickly
- **Higher INITIAL_VOLATILITY**: Expect more erratic performance
- **Higher TAU**: Volatility changes more quickly

### Session Filtering

Control which sessions are included in ratings:

```python
# Minimum players required for a session to count
MIN_PLAYERS_PER_SESSION = 5

# Minimum fight time (seconds) for valid performance
MIN_FIGHT_TIME = 60

# Maximum allowed metric values (outlier detection)
MAX_DPS = 10000
MAX_HEALING = 5000
```

### Date-Based Filtering

The system supports time-window analysis:

```python
def parse_date_filter(date_filter):
    if date_filter == '30d':
        return datetime.now() - timedelta(days=30)
    elif date_filter == '90d':
        return datetime.now() - timedelta(days=90)
    elif date_filter == '180d':
        return datetime.now() - timedelta(days=180)
    return None
```

Add new time windows by extending this function and updating the UI.

## Performance Optimization

### Database Indexing

Ensure proper indexes for rating calculations:

```sql
CREATE INDEX IF NOT EXISTS idx_timestamp ON player_performances(timestamp);
CREATE INDEX IF NOT EXISTS idx_parsed_date ON player_performances(parsed_date);
CREATE INDEX IF NOT EXISTS idx_account_profession ON player_performances(account_name, profession);
CREATE INDEX IF NOT EXISTS idx_metric_category ON glicko_ratings(metric_category);
```

### Incremental Updates

For large datasets, implement incremental rating updates:

```python
def incremental_rating_update(db_path, new_sessions_only=True):
    # Only process sessions newer than last rating calculation
    # Store last_update timestamp in database
    # Skip recalculating unchanged sessions
```

### Memory Management

For very large datasets:

```python
# Process sessions in batches
BATCH_SIZE = 100

def process_sessions_in_batches(sessions):
    for i in range(0, len(sessions), BATCH_SIZE):
        batch = sessions[i:i + BATCH_SIZE]
        process_batch(batch)
        # Clear memory between batches
        gc.collect()
```

## Quality Assurance

### Rating Validation

Implement checks to ensure rating integrity:

```python
def validate_ratings(db_path):
    conn = sqlite3.connect(db_path)
    
    # Check for reasonable rating ranges
    cursor = conn.execute("""
        SELECT metric_category, MIN(rating), MAX(rating), AVG(rating)
        FROM glicko_ratings
        GROUP BY metric_category
    """)
    
    for metric, min_rating, max_rating, avg_rating in cursor:
        if min_rating < 800 or max_rating > 2500:
            print(f"WARNING: {metric} has unusual rating range: {min_rating}-{max_rating}")
        
        if avg_rating < 1400 or avg_rating > 1600:
            print(f"WARNING: {metric} has unusual average rating: {avg_rating}")
```

### Outlier Detection

Detect and handle statistical outliers:

```python
def detect_performance_outliers(session_data, metric):
    values = [p[metric] for p in session_data if p[metric] > 0]
    if len(values) < 5:
        return []
    
    q1 = numpy.percentile(values, 25)
    q3 = numpy.percentile(values, 75)
    iqr = q3 - q1
    
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    outliers = []
    for player in session_data:
        if player[metric] < lower_bound or player[metric] > upper_bound:
            outliers.append(player)
    
    return outliers
```

## Testing and Validation

### Unit Tests

Create tests for core functions:

```python
import unittest

class TestGlickoRating(unittest.TestCase):
    def test_rating_update(self):
        # Test basic rating update
        old_rating = 1500
        new_rating = update_rating(old_rating, rd=200, z_score=1.0)
        self.assertGreater(new_rating, old_rating)
    
    def test_z_score_calculation(self):
        # Test z-score normalization
        session_data = [
            {'account_name': 'A', 'dps': 1000},
            {'account_name': 'B', 'dps': 2000},
            {'account_name': 'C', 'dps': 3000}
        ]
        z_scores = calculate_z_scores(session_data, 'dps')
        self.assertAlmostEqual(z_scores['B'], 0.0, places=2)
```

### Integration Tests

Test the full pipeline:

```python
def test_full_pipeline():
    # Create test database
    # Insert test data
    # Run rating calculation
    # Verify expected results
    # Clean up test database
```

### Historical Validation

Compare ratings against known performance:

```python
def validate_against_known_performance():
    # Check that known top performers have high ratings
    # Verify profession specialists rank well in their metrics
    # Ensure rating stability over time
```

## Troubleshooting

### Common Issues

**Ratings Not Updating:**
1. Check if new sessions are being parsed
2. Verify metric data is non-zero
3. Ensure minimum session requirements are met

**Extreme Ratings:**
1. Check for data outliers in recent sessions
2. Verify z-score calculations are reasonable
3. Review session composition (very small or very large groups)

**Missing Profession Data:**
1. Verify profession names match exactly
2. Check that weighted metrics exist for all professions
3. Ensure profession appears in sufficient sessions

### Debug Tools

```python
# Check rating calculation details
def debug_rating_calculation(account_name, profession, metric):
    # Print intermediate values
    # Show z-scores for recent sessions
    # Display rating update steps

# Analyze session statistics
def analyze_session(timestamp):
    # Show player count, metric distributions
    # Identify potential issues
    # Compare to other sessions
```

This rating system provides a robust foundation for skill assessment that can evolve with the game meta and community needs.