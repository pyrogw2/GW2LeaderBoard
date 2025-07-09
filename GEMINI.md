This is a comprehensive project for creating a Guild Wars 2 WvW leaderboard. Here's a breakdown of the project based on the provided documentation.

### Project Summary

This project is a Guild Wars 2 World vs. World (WvW) leaderboard system. It processes combat logs in TiddlyWiki format, calculates player skill ratings using the Glicko-2 system, and generates a static web UI to display the leaderboards. The system is designed to be automated, with features for syncing new logs, filtering by guild, and analyzing performance across various metrics.

### Core Components

*   **`sync_logs.py`**: Fetches new combat logs from an aggregate site, downloads them, and triggers the processing pipeline.
*   **`parse_logs_enhanced.py`**: Parses the TiddlyWiki HTML and JSON files to extract player performance data. It tracks 11 different metrics.
*   **`glicko_rating_system.py`**: Implements the Glicko-2 rating algorithm. It calculates player ratings for each metric based on their performance in combat sessions.
*   **`generate_web_ui.py`**: Creates a static HTML, CSS, and JavaScript web interface to display the leaderboards. The UI is interactive, with features like player modals, dark mode, and filtering.
*   **`guild_manager.py`**: Integrates with the Guild Wars 2 API to fetch guild member information, allowing for guild-specific filtering on the leaderboards.

### Data Flow

1.  **Log Collection**: `sync_logs.py` finds and downloads new TiddlyWiki logs.
2.  **Parsing**: `parse_logs_enhanced.py` extracts player performance data from the logs and stores it in an SQLite database (`gw2_comprehensive.db`).
3.  **Rating Calculation**: `glicko_rating_system.py` processes the performance data to calculate Glicko-2 ratings for each player in various categories.
4.  **UI Generation**: `generate_web_ui.py` queries the database for the latest ratings and generates the web UI files.
5.  **Guild Filtering**: `guild_manager.py` keeps a local cache of guild members to allow for filtering the leaderboards.

### Key Features

*   **Glicko-2 Rating System**: A more advanced rating system than Elo, which accounts for the uncertainty and volatility of a player's rating.
*   **Comprehensive Metrics**: Tracks 11 different performance metrics, including DPS, healing, boon strips, and more.
*   **Interactive Web UI**: The generated website is modern and interactive, with features like player-specific details, dark mode, and various filtering options.
*   **Guild Integration**: Can filter the leaderboards to show only members of a specific guild.
*   **Automation**: The entire process, from fetching logs to generating the UI, can be automated.

### How to Use

1.  **Setup**: Install the required Python libraries (`requests`, `beautifulsoup4`).
2.  **Get Logs**: Either configure `sync_logs.py` to fetch logs automatically or manually place them in the `extracted_logs` directory.
3.  **Process Logs**: Run `parse_logs_enhanced.py` to populate the database.
4.  **Calculate Ratings**: Run `glicko_rating_system.py` to calculate the Glicko-2 ratings.
5.  **Generate UI**: Run `generate_web_ui.py` to create the web interface.
6.  **View**: Open the `index.html` file in the output directory to see the leaderboards.

### Common Commands

*   **Full automated processing of new logs**:
    `python sync_logs.py --auto-confirm`
*   **Manual log processing**:
    `python parse_logs_enhanced.py extracted_logs/ -d gw2_comprehensive.db`
    `python glicko_rating_system.py gw2_comprehensive.db --recalculate`
*   **Generate web interface**:
    `python generate_web_ui.py gw2_comprehensive.db -o web_ui_output`

This `GEMINI.md` file should provide a good starting point for understanding and working with this project.