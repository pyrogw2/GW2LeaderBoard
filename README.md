# GW2 WvW Leaderboard System

[![CI](https://github.com/pyrogw2/GW2LeaderBoard/actions/workflows/ci.yml/badge.svg)](https://github.com/pyrogw2/GW2LeaderBoard/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/pyrogw2/GW2LeaderBoard)](https://github.com/pyrogw2/GW2LeaderBoard/releases/latest)

An automated system for parsing Guild Wars 2 World vs World combat logs and generating skill-based rankings using the Glicko-2 rating system with advanced statistical analysis.

## 🏆 Features

- **11 Performance Metrics**: DPS, healing, barrier, cleanses, strips, stability, resistance, might, protection, down contribution, and burst consistency
- **High Scores System**: Record-breaking single performance instances (highest burst damage, skill damage, single-fight DPS)
- **Glicko-2 Rating System**: Pure skill ratings with uncertainty and volatility tracking
- **Player Summary Modal**: Click any player name for detailed performance breakdowns by profession and metric
- **Profession-Specific Rankings**: Weighted leaderboards for different WvW roles with automatic build detection
- **Guild Integration**: GW2 API integration for guild member filtering and tracking
- **Time-Based Filtering**: View performance across different time periods (All Time, 30d, 90d, 180d)
- **Automated Sync**: Smart detection and processing of new combat logs
- **Static Web Interface**: Deploy anywhere with interactive sorting, filtering, and dark mode support

## 🚀 Quick Start

### Option 1: GUI Application (Recommended for beginners)
1. **Download** the executable for your platform from [Releases](https://github.com/pyrogw2/GW2LeaderBoard/releases)
2. **Configure** by copying `sync_config.json.example` to `sync_config.json` and editing it
3. **Run** the executable and use the graphical interface

### Option 2: Command Line

```bash
# 1. Check for new logs and process them automatically
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
| **Protection** | Protection generation | Support |
| **Down Contribution** | Damage to downed enemies | All |
| **Burst Consistency** | Sustained high burst damage | DPS |

## 🎯 Advanced Features

### High Scores System
- **Highest 1 Sec Burst**: Peak burst damage in a single second
- **Highest Outgoing Skill Damage**: Single highest skill damage dealt
- **Highest Incoming Skill Damage**: Single highest skill damage received
- **Highest Single Fight DPS**: Best DPS performance in a single encounter

### Player Analysis
- **Interactive Player Modals**: Click any player name to view detailed breakdowns
- **Profession-Based Filtering**: View metrics filtered by specific professions/builds
- **Guild Member Integration**: Automatic detection and filtering of guild members
- **Performance Trends**: Track improvement over different time periods

### Profession Recognition
- **Automatic Build Detection**: China DH, Boon Vindicator, and other variants
- **Weighted Metrics**: Different professions evaluated on role-appropriate metrics
- **Specialized Leaderboards**: Separate rankings for each profession with custom weightings

## ⚙️ Requirements

- **Python 3.7+** with `requests` and `beautifulsoup4` libraries
- **TiddlyWiki combat logs** (extracted or direct)
- **Modern web browser** for viewing leaderboards
- **GW2 API Key** (optional, for guild features)

```bash
pip install requests beautifulsoup4
```

## 📖 Documentation

Comprehensive documentation is available in the `docs/` directory:

### User Documentation
- **[Getting Started](docs/GETTING_STARTED.md)** - Complete setup walkthrough
- **[Daily Usage](docs/DAILY_USAGE.md)** - Routine operations and maintenance  
- **[System Overview](docs/SYSTEM_OVERVIEW.md)** - Architecture and design
- **[Glicko System](docs/GLICKO_SYSTEM.md)** - Rating algorithm and customization
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Configuration](docs/CONFIGURATION.md)** - All settings and options
- **[API Reference](docs/API_REFERENCE.md)** - Database schema and technical details

### Development Documentation
- **[Contributing Guide](docs/development/CONTRIBUTING.md)** - Code contribution guidelines
- **[Development Summary](docs/development/DEVELOPMENT_SUMMARY.md)** - Recent development progress
- **[Executable Build Guide](docs/development/EXECUTABLE_BUILD.md)** - Creating standalone executables
- **[AI Assistant Notes](docs/development/GEMINI.md)** - AI development context

**📚 Full Documentation Index**: [docs/README.md](docs/README.md)

## 🔧 Core Components

- **`parse_logs_enhanced.py`** - Extracts performance data from TiddlyWiki logs
- **`glicko_rating_system.py`** - Calculates skill ratings using Glicko-2 algorithm
- **`generate_web_ui.py`** - Creates interactive web interface with player modals
- **`sync_logs.py`** - Automated log discovery and processing
- **`guild_manager.py`** - GW2 API integration for guild member management

## 🌐 Example Output

The system generates professional leaderboards with:

- **Individual metric rankings** (DPS, Healing, etc.)
- **High Scores leaderboards** with record-breaking performances
- **Profession-specific leaderboards** with role-appropriate weightings
- **Interactive player modals** showing detailed performance by profession
- **Date filtering** (All Time, 30d, 90d, 180d)
- **Guild member filtering** with GW2 API integration
- **Glicko-2 ratings** showing pure skill level with uncertainty tracking
- **Dark mode support** and responsive design

## 🎯 Use Cases

- **Guild Performance Tracking** - Monitor member improvement with detailed player analysis
- **Meta Analysis** - Understand profession effectiveness across different time periods
- **Recruitment** - Identify skilled players across different roles with comprehensive metrics
- **Personal Improvement** - Track your own skill development with profession-specific insights
- **Community Leaderboards** - Public rankings with interactive features for server communities
- **Record Tracking** - High scores system for celebrating exceptional performances

## 🔄 Automated Workflow

1. **Sync** detects new logs from configured sources
2. **Parser** extracts 11 performance metrics from TiddlyWiki format
3. **Rating System** calculates pure Glicko-2 ratings using session-based z-scores
4. **Guild Manager** integrates GW2 API data for member filtering
5. **Generator** creates updated web interface with interactive player modals
6. **Deploy** static files to any web hosting platform

## 📈 Rating System

Uses the **Glicko-2 rating system** (enhanced Elo) with:

- **Session-based comparison** - Players ranked against others in same fight
- **Z-score normalization** - Fair comparison across different group skill levels  
- **Pure skill ratings** - No artificial bonuses or composite scoring
- **Uncertainty tracking** - More/less confident ratings based on game count
- **Volatility measurement** - Consistency of performance over time
- **Profession weighting** - Different metrics matter for different roles

## 🏗️ Architecture

```
Combat Logs (TiddlyWiki) → Parser → Database (SQLite) → Rating Engine → Web UI
                            ↑                              ↑         ↑
                      Sync Service ←------------------  Guild API  Modal System
```

**Database**: SQLite with performance data, ratings, and guild member cache  
**Web Interface**: Static HTML/CSS/JS with interactive modals and dark mode  
**Sync**: Automated detection and processing of new logs  
**Rating Engine**: Pure Glicko-2 algorithm with WvW-specific adaptations  
**Guild Integration**: GW2 API v2 for member validation and filtering

## 💻 Executable Distributions

Pre-built executables are available for easy installation:

- **Windows**: `workflow_ui.exe` - Single-file executable with GUI
- **macOS**: `GW2 Leaderboard.app` - Native application bundle  
- **Linux**: `gw2-leaderboard` - Standalone binary

**Download from:** [GitHub Releases](https://github.com/pyrogw2/GW2LeaderBoard/releases)

### Features:
- ✅ No Python installation required
- ✅ Graphical user interface for all operations
- ✅ Built-in console output and progress tracking
- ✅ Configuration editor with validation
- ✅ All command-line functionality available

For building executables yourself, see [EXECUTABLE_BUILD.md](EXECUTABLE_BUILD.md).

## 🤝 Contributing

We welcome contributions to the GW2 WvW Leaderboards project! This system is designed for the Guild Wars 2 WvW community.

### How to Contribute

1. **Read our [Contributing Guide](CONTRIBUTING.md)** for development standards and workflow
2. **Check out our [Issues](https://github.com/pyrogw2/GW2LeaderBoard/issues)** for tasks to work on
3. **Follow our git workflow** with conventional commits and feature branches
4. **Run tests** locally before submitting PRs
5. **Update documentation** for any new features

### Areas We Need Help With

- 🏆 New metrics and profession support
- ⚡ Performance optimizations  
- 🎨 UI improvements and accessibility
- 📚 Documentation enhancements
- 🐛 Bug fixes and testing
- 🔗 Guild and API integrations
- 🧪 Test coverage improvements

### Development Standards

- **Git Workflow**: Feature branches with conventional commits
- **Testing**: All PRs must pass CI tests
- **Code Quality**: Follow Python best practices
- **Documentation**: Update docs for user-facing changes

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

Provided as-is for the Guild Wars 2 community. See individual files for specific licensing terms.