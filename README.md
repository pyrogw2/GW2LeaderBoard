# GW2 WvW Leaderboard System

An automated system for parsing Guild Wars 2 World vs World combat logs and generating skill-based rankings using the Glicko rating system.

## 🏆 Features

- **9 Performance Metrics**: DPS, healing, barrier, cleanses, strips, stability, resistance, might, and down contribution
- **Glicko Rating System**: Advanced skill ratings with uncertainty and volatility tracking
- **Profession-Specific Rankings**: Weighted leaderboards for different WvW roles
- **Time-Based Filtering**: View performance across different time periods
- **Automated Sync**: Smart detection and processing of new combat logs
- **Static Web Interface**: Deploy anywhere with interactive sorting and filtering

## 🚀 Quick Start

```bash
# 1. Check for new logs and process them
python sync_logs.py --auto-confirm

# 2. Or manually process existing logs
python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db
python glicko_rating_system.py gw2_comprehensive.db --recalculate

# 3. Generate web interface
python generate_web_ui.py gw2_comprehensive.db -o web_ui_output

# 4. Open web_ui_output/index.html in your browser
```

## 📊 What It Tracks

| Metric | Purpose | Role Focus |
|--------|---------|------------|
| **DPS** | Damage to enemy players | All |
| **Healing** | Healing output | Support |
| **Barrier** | Barrier generation | Support |
| **Cleanses** | Condition removal | Support |
| **Strips** | Boon removal | Support |
| **Stability** | Stability generation | Support |
| **Resistance** | Resistance generation | Support |
| **Might** | Might generation | Support |
| **Down Contribution** | Damage to down enemies | All |

## ⚙️ Requirements

- **Python 3.7+** with `requests` library
- **TiddlyWiki combat logs** (extracted or direct)
- **Modern web browser** for viewing leaderboards

```bash
pip install requests
```

## 📖 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Getting Started](docs/GETTING_STARTED.md)** - Complete setup walkthrough
- **[Daily Usage](docs/DAILY_USAGE.md)** - Routine operations and maintenance  
- **[System Overview](docs/SYSTEM_OVERVIEW.md)** - Architecture and design
- **[Glicko System](docs/GLICKO_SYSTEM.md)** - Rating algorithm and customization
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Configuration](docs/CONFIGURATION.md)** - All settings and options
- **[API Reference](docs/API_REFERENCE.md)** - Database schema and technical details

## 🔧 Core Components

- **`parse_logs_enhanced.py`** - Extracts performance data from TiddlyWiki logs
- **`glicko_rating_system.py`** - Calculates skill ratings using Glicko algorithm
- **`generate_web_ui.py`** - Creates interactive web interface
- **`sync_logs.py`** - Automated log discovery and processing

## 🌐 Example Output

The system generates professional leaderboards with:

- **Individual metric rankings** (DPS, Healing, etc.)
- **Profession-specific leaderboards** with role-appropriate weightings
- **Date filtering** (All Time, 30d, 90d, 180d)
- **Glicko ratings** showing skill level and confidence
- **Composite scores** combining multiple performance factors

## 🎯 Use Cases

- **Guild Performance Tracking** - Monitor member improvement over time
- **Meta Analysis** - Understand profession effectiveness in different periods
- **Recruitment** - Identify skilled players across different roles
- **Personal Improvement** - Track your own skill development
- **Community Leaderboards** - Public rankings for server communities

## 🔄 Automated Workflow

1. **Sync** detects new logs from configured sources
2. **Parser** extracts performance metrics from TiddlyWiki format
3. **Rating System** calculates Glicko ratings using session-based z-scores
4. **Generator** creates updated web interface with latest rankings
5. **Deploy** static files to any web hosting platform

## 📈 Rating System

Uses the **Glicko rating system** (enhanced Elo) with:

- **Session-based comparison** - Players ranked against others in same fight
- **Z-score normalization** - Fair comparison across different group skill levels  
- **Uncertainty tracking** - More/less confident ratings based on game count
- **Volatility measurement** - Consistency of performance over time
- **Profession weighting** - Different metrics matter for different roles

## 🏗️ Architecture

```
Combat Logs (TiddlyWiki) → Parser → Database (SQLite) → Rating Engine → Web UI
                            ↑                              ↑
                      Sync Service ←------------------  Automation
```

**Database**: SQLite with performance data and calculated ratings  
**Web Interface**: Static HTML/CSS/JS (deploy anywhere)  
**Sync**: Automated detection and processing of new logs  
**Rating Engine**: Glicko algorithm with WvW-specific adaptations

## 🤝 Contributing

This system is designed for the Guild Wars 2 WvW community. Contributions welcome for:

- New metrics and profession support
- Performance optimizations  
- UI improvements
- Documentation enhancements
- Bug fixes and testing

## 📄 License

Provided as-is for the Guild Wars 2 community. See individual files for specific licensing terms.