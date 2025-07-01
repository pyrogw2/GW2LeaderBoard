# GW2 WvW Leaderboard System Overview

## Architecture

The GW2 WvW Leaderboard System is a comprehensive solution for analyzing World vs World combat performance using advanced statistical methods. The system processes TiddlyWiki-format combat logs and generates skill-based rankings using the Glicko rating system.

## Component Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Combat Logs   │───▶│   Log Parser     │───▶│   Database      │
│  (TiddlyWiki)   │    │                  │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                          │
┌─────────────────┐    ┌──────────────────┐             │
│   Web Interface │◀───│  UI Generator    │◀─────────────┤
│ (HTML/CSS/JS)   │    │                  │             │
└─────────────────┘    └──────────────────┘             │
                                                          │
┌─────────────────┐    ┌──────────────────┐             │
│  Sync Service   │───▶│  Glicko System   │◀─────────────┘
│ (Automation)    │    │ (Rating Engine)  │
└─────────────────┘    └──────────────────┘
```

## Data Flow

### 1. Log Ingestion
- **Input**: TiddlyWiki HTML files containing combat session data
- **Process**: Parse offensive stats tables to extract player performance metrics
- **Output**: Structured performance data stored in SQLite database

### 2. Rating Calculation
- **Input**: Raw performance data from multiple sessions
- **Process**: Apply Glicko rating algorithm with session-based z-score normalization
- **Output**: Skill ratings and composite scores for each player/profession/metric

### 3. UI Generation
- **Input**: Processed ratings and performance data
- **Process**: Generate static HTML/CSS/JS with interactive leaderboards
- **Output**: Deployable web interface with filtering and sorting capabilities

### 4. Automation
- **Input**: Configuration for log sources and processing parameters
- **Process**: Monitor for new logs, download, and run full pipeline
- **Output**: Always up-to-date leaderboards with minimal manual intervention

## Core Technologies

### Database Schema
- **player_performances**: Raw session data (1,368+ records)
- **glicko_ratings**: Calculated skill ratings by metric category
- **Indexes**: Optimized for date filtering and metric queries

### Rating Algorithm
- **Base System**: Glicko rating algorithm (enhanced Elo with uncertainty)
- **Normalization**: Session-based z-score calculation for fair comparison
- **Composite Scoring**: Weighted combination of Glicko rating and percentile rank

### Metrics Tracked
1. **DPS** - Damage per second to enemy players
2. **Healing** - Healing output per second  
3. **Barrier** - Barrier generation per second
4. **Cleanses** - Condition removal per second
5. **Strips** - Boon removal per second
6. **Stability** - Stability generation per second
7. **Resistance** - Resistance generation per second
8. **Might** - Might generation per second
9. **Down Contribution** - Damage contributed to downing enemies per second

## Key Features

### Session-Based Analysis
- Each combat session is analyzed independently
- Player performance compared to others in the same session
- Accounts for varying group compositions and skill levels

### Profession-Specific Rankings
- Weighted metrics based on profession role (DPS, Support, etc.)
- Separate leaderboards for each profession
- Role-appropriate performance evaluation

### Time-Based Filtering
- All Time rankings for overall skill assessment
- Recent performance windows (30d, 90d, 180d)
- Trend analysis and improvement tracking

### Automated Maintenance
- Smart log detection from aggregate sites
- Duplicate prevention and error handling
- Full pipeline automation with user oversight

## Scalability & Performance

### Current Capacity
- Handles 31+ combat sessions efficiently
- Processes ~1,400 player performance records
- Generates comprehensive UI in under 30 seconds

### Growth Considerations
- SQLite database suitable for moderate scale (thousands of sessions)
- Static UI generation scales to any hosting platform
- Rating calculations optimized for incremental updates

## Security & Reliability

### Data Integrity
- Comprehensive input validation and sanitization
- Transaction-based database operations
- Backup-friendly single-file database

### Error Handling
- Graceful degradation when logs are malformed
- Detailed logging and progress reporting
- Recovery mechanisms for partial failures

## Deployment Models

### Local Development
- Complete system runs on single machine
- Database, processing, and UI generation all local
- Ideal for testing and small group usage

### Distributed Deployment
- Database on dedicated server
- UI deployed to CDN/static hosting
- Processing can be scheduled/automated

### Community Hosting
- GitHub Pages for UI hosting
- Automated processing via GitHub Actions
- Public leaderboards with regular updates

## Extension Points

### New Metrics
- Add columns to database schema
- Update parser extraction logic
- Include in rating system configuration

### Custom Professions
- Define metric weightings in configuration
- Add profession-specific UI elements
- Update icon mappings and display logic

### Advanced Analytics
- Historical trend analysis
- Performance prediction models
- Advanced statistical visualizations

## Quality Assurance

### Data Validation
- Input sanitization prevents code injection
- Schema validation ensures data consistency
- Cross-referencing detects anomalies

### Performance Monitoring
- Processing time tracking
- Database query optimization
- UI rendering performance measurement

### Testing Strategy
- Unit tests for core algorithms
- Integration tests for pipeline components
- Manual verification against known data sets