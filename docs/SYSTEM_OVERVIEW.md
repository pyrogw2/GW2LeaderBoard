# GW2 WvW Leaderboard System Overview

## Architecture

The GW2 WvW Leaderboard System is a comprehensive solution for analyzing World vs World combat performance using advanced statistical methods. The system processes TiddlyWiki-format combat logs and generates skill-based rankings using the pure Glicko-2 rating system with interactive player analysis.

## Component Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Combat Logs   │───▶│   Log Parser     │───▶│   Database      │
│  (TiddlyWiki)   │    │ (11 Metrics)     │    │   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                          │
┌─────────────────┐    ┌──────────────────┐             │
│   Web Interface │◀───│  UI Generator    │◀─────────────┤
│ (HTML/CSS/JS)   │    │ (Player Modals)  │             │
└─────────────────┘    └──────────────────┘             │
                                                          │
┌─────────────────┐    ┌──────────────────┐             │
│  Sync Service   │───▶│ Glicko-2 System  │◀─────────────┤
│ (Automation)    │    │ (Pure Ratings)   │             │
└─────────────────┘    └──────────────────┘             │
                                                          │
┌─────────────────┐    ┌──────────────────┐             │
│  Guild Manager  │───▶│ High Scores      │◀─────────────┘
│  (GW2 API)      │    │ (Records)        │
└─────────────────┘    └──────────────────┘
```

## Data Flow

### 1. Log Ingestion
- **Input**: TiddlyWiki HTML files containing combat session data
- **Process**: Parse offensive stats tables to extract 11 performance metrics per player
- **Output**: Structured performance data stored in SQLite database with guild member integration

### 2. Rating Calculation
- **Input**: Raw performance data from multiple sessions
- **Process**: Apply pure Glicko-2 rating algorithm with session-based z-score normalization
- **Output**: Skill ratings without composite scoring for each player/profession/metric combination

### 3. UI Generation
- **Input**: Processed ratings, performance data, and guild information
- **Process**: Generate static HTML/CSS/JS with interactive player modals and profession filtering
- **Output**: Deployable web interface with dark mode, responsive design, and clickable player analysis

### 4. Guild Integration
- **Input**: GW2 API key and guild configuration
- **Process**: Fetch and cache guild member data from GW2 API v2
- **Output**: Guild member filtering and identification in leaderboards

### 5. High Scores Tracking
- **Input**: Individual performance instances from combat sessions
- **Process**: Track record-breaking performances across different categories
- **Output**: High scores leaderboards separate from skill-based ratings

### 6. Automation
- **Input**: Configuration for log sources and processing parameters
- **Process**: Monitor for new logs, download, and run full pipeline with guild updates
- **Output**: Always up-to-date leaderboards with minimal manual intervention

## Core Technologies

### Database Schema
- **`player_performances`**: Raw session data with 11 metrics per player
- **`glicko_ratings`**: Calculated pure Glicko-2 skill ratings by metric category
- **`high_scores`**: Record-breaking performance instances
- **`guild_members`**: Cached GW2 API guild member data
- **Indexes**: Optimized for date filtering, guild queries, and metric lookups

### Rating Algorithm
- **Base System**: Pure Glicko-2 rating algorithm (enhanced Elo with uncertainty)
- **Normalization**: Session-based z-score calculation for fair comparison
- **No Composite Scoring**: Direct Glicko ratings used for rankings without artificial bonuses

### Metrics Tracked (11 Total)
1. **DPS** - Damage per second to enemy players
2. **Healing** - Healing output per second  
3. **Barrier** - Barrier generation per second
4. **Cleanses** - Condition removal per second
5. **Strips** - Boon removal per second
6. **Stability** - Stability generation per second
7. **Resistance** - Resistance generation per second
8. **Might** - Might generation per second
9. **Protection** - Protection generation per second
10. **Down Contribution** - Damage contributed to downing enemies per second
11. **Burst Consistency** - Sustained high burst damage performance

### High Scores Categories
1. **Highest 1 Sec Burst** - Peak burst damage in a single second
2. **Highest Outgoing Skill Damage** - Single highest skill damage dealt
3. **Highest Incoming Skill Damage** - Single highest skill damage received
4. **Highest Single Fight DPS** - Best DPS performance in a single encounter

## Key Features

### Interactive Player Analysis
- **Clickable Player Names** - Click any player in leaderboards to view detailed modal
- **Profession-Based Filtering** - View metrics filtered by specific professions/builds
- **Performance Breakdown** - Detailed analysis by profession and metric with game counts
- **Guild Status Integration** - Visual indication of guild membership status

### Session-Based Analysis
- Each combat session is analyzed independently
- Player performance compared to others in the same session
- Accounts for varying group compositions and skill levels
- Z-score normalization ensures fair comparison across different battle types

### Profession-Specific Rankings
- Weighted metrics based on profession role (DPS, Support, etc.)
- Separate leaderboards for each profession with custom metric combinations
- Automatic build detection (China DH, Boon Vindicator, etc.)
- Role-appropriate performance evaluation

### Time-Based Filtering
- All Time rankings for overall skill assessment
- Recent performance windows (30d, 90d, 180d)
- Date-filtered rating calculations with temporary databases
- Trend analysis and improvement tracking

### Guild Management
- **GW2 API Integration** - Automatic guild member detection and caching
- **Member Filtering** - Toggle between all players and guild members only
- **Guild Status Tracking** - Visual indicators and filtering options
- **API Key Management** - Secure configuration for guild features

### Automated Maintenance
- Smart log detection from aggregate sites
- Duplicate prevention and error handling
- Full pipeline automation with user oversight
- Guild data refresh and synchronization

## Scalability & Performance

### Current Capacity
- Handles 31+ combat sessions efficiently
- Processes ~1,400+ player performance records
- Generates comprehensive UI with parallel processing in under 30 seconds
- Supports guild member lists of 100+ members

### Growth Considerations
- SQLite database suitable for moderate scale (thousands of sessions)
- Static UI generation scales to any hosting platform
- Pure Glicko-2 calculations optimized for incremental updates
- Guild API caching reduces external dependencies

### Performance Optimizations
- **Parallel Processing** - Multi-threaded UI generation for different time periods
- **Database Indexing** - Optimized queries for date filtering and guild lookups
- **Temporary Databases** - Isolated calculations for date-filtered ratings
- **Efficient Caching** - Guild member data cached locally to reduce API calls

## Security & Reliability

### Data Integrity
- Comprehensive input validation and sanitization
- Transaction-based database operations
- Backup-friendly single-file database with guild data preservation
- API key security and rate limiting

### Error Handling
- Graceful degradation when logs are malformed
- Guild API fallback when external services unavailable
- Detailed logging and progress reporting
- Recovery mechanisms for partial failures

### Guild Data Security
- API keys stored in local configuration only
- Guild member data cached with expiration
- No sensitive player data transmitted or stored beyond what's necessary

## Deployment Models

### Local Development
- Complete system runs on single machine
- Database, processing, guild integration, and UI generation all local
- Ideal for testing and small group usage

### Distributed Deployment
- Database on dedicated server with guild data
- UI deployed to CDN/static hosting
- Processing can be scheduled/automated with guild refresh cycles

### Community Hosting
- GitHub Pages for UI hosting
- Automated processing via GitHub Actions
- Public leaderboards with regular updates and guild integration

## Extension Points

### New Metrics
- Add columns to database schema
- Update parser extraction logic for new TiddlyWiki fields
- Include in rating system configuration and UI

### Custom Professions
- Define metric weightings in configuration
- Add profession-specific UI elements and build detection
- Update icon mappings and display logic

### Advanced Analytics
- Historical trend analysis with guild progression tracking
- Performance prediction models
- Advanced statistical visualizations
- Cross-guild comparison features

### Guild Features
- Multi-guild support and comparison
- Guild-specific leaderboards and statistics
- Member progression tracking
- Recruitment assistance tools

## Quality Assurance

### Data Validation
- Input sanitization prevents code injection
- Schema validation ensures data consistency
- Cross-referencing detects anomalies
- Guild API data validation and rate limiting

### Performance Monitoring
- Processing time tracking across all components
- Database query optimization
- UI rendering performance measurement
- Guild API response time monitoring

### Testing Strategy
- Unit tests for core algorithms including guild integration
- Integration tests for pipeline components
- Manual verification against known data sets
- Guild API integration testing

This system provides a robust foundation for WvW performance analysis that scales with community needs while maintaining data integrity and providing rich interactive features for player and guild analysis.