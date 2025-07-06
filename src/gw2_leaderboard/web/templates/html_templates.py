"""
HTML templates for GW2 WvW Leaderboards web UI.
"""

def get_main_html_template() -> str:
    """Return the main HTML template for the web UI."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GW2 WvW Leaderboards</title>
    <link rel="stylesheet" href="styles.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <div class="header-text">
                    <h1>🏆 GW2 WvW Leaderboards</h1>
                    <p class="subtitle">Glicko-based rating system for World vs World performance</p>
                    <p class="last-updated">Last updated: <span id="lastUpdated"></span></p>
                </div>
                <button class="dark-mode-toggle" id="darkModeToggle" aria-label="Toggle dark mode">
                    <span class="toggle-icon">🌙</span>
                </button>
            </div>
        </header>

        <nav class="nav-tabs">
            <button class="tab-button active" data-tab="individual">Individual Metrics</button>
            <button class="tab-button" data-tab="high-scores">High Scores</button>
            <button class="tab-button" data-tab="professions">Professions</button>
            <button class="tab-button" data-tab="player-stats">Player Stats</button>
            <button class="tab-button" data-tab="about">About</button>
        </nav>

        <div class="modern-filters">
            <!-- Segmented Control for Time Period -->
            <div class="segmented-control">
                <input type="radio" name="time-filter" id="time-30" value="30d" checked>
                <label for="time-30">30d</label>
                <input type="radio" name="time-filter" id="time-60" value="60d">
                <label for="time-60">60d</label>
                <input type="radio" name="time-filter" id="time-90" value="90d">
                <label for="time-90">90d</label>
                <input type="radio" name="time-filter" id="time-all" value="overall">
                <label for="time-all">All</label>
            </div>

            <!-- Guild Filter Chips -->
            <div class="filter-chips" id="guild-chips" style="display: none;">
                <div class="chip active" data-guild-filter="all_players">👥 All</div>
                <div class="chip" data-guild-filter="guild_members" id="guild-chip">🛡️ Guild</div>
            </div>

            <!-- Modern Toggle for Rating Deltas -->
            <div class="delta-toggle">
                <span class="toggle-label">📈 Latest Change</span>
                <label class="toggle-switch">
                    <input type="checkbox" id="show-rating-deltas">
                    <span class="toggle-slider"></span>
                </label>
            </div>
        </div>

        <main>
            <!-- Individual Metrics -->
            <div id="individual" class="tab-content active">
                <h2>Individual Metrics</h2>
                <p class="description">Rankings by specific performance metrics.</p>
                
                <div class="metric-selector">
                    <button class="metric-button active" data-metric="DPS">DPS</button>
                    <button class="metric-button" data-metric="Healing">Healing</button>
                    <button class="metric-button" data-metric="Barrier">Barrier</button>
                    <button class="metric-button" data-metric="Cleanses">Cleanses</button>
                    <button class="metric-button" data-metric="Strips">Strips</button>
                    <button class="metric-button" data-metric="Stability">Stability</button>
                    <button class="metric-button" data-metric="Resistance">Resistance</button>
                    <button class="metric-button" data-metric="Might">Might</button>
                    <button class="metric-button" data-metric="Protection">Protection</button>
                    <button class="metric-button" data-metric="Downs">DownCont</button>
                    <button class="metric-button" data-metric="Burst Consistency">Burst</button>
                    <button class="metric-button" data-metric="Distance to Tag">Distance</button>
                </div>
                
                <div class="search-container">
                    <input type="text" id="individual-search" class="search-input" placeholder="Search players, professions, or accounts...">
                    <button class="search-clear" onclick="clearSearch('individual')">&times;</button>
                </div>
                <div id="individual-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- High Scores -->
            <div id="high-scores" class="tab-content">
                <h2>High Scores</h2>
                <p class="description">Top performance records across different categories (non-Glicko based).</p>
                
                <div class="metric-selector">
                    <button class="metric-button active" data-metric="Highest 1 Sec Burst">Highest 1 Sec Burst</button>
                    <button class="metric-button" data-metric="Highest Outgoing Skill Damage">Highest Outgoing Skill Damage</button>
                    <button class="metric-button" data-metric="Highest Incoming Skill Damage">Highest Incoming Skill Damage</button>
                    <button class="metric-button" data-metric="Highest Single Fight DPS">Highest Single Fight DPS</button>
                </div>
                
                <div class="search-container">
                    <input type="text" id="high-scores-search" class="search-input" placeholder="Search players, professions, or accounts...">
                    <button class="search-clear" onclick="clearSearch('high-scores')">&times;</button>
                </div>
                <div id="high-scores-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- Profession Leaderboards -->
            <div id="professions" class="tab-content">
                <h2>Profession Leaderboards</h2>
                <p class="description">Role-specific rankings with weighted metrics for each profession.</p>
                
                <div class="profession-selector">
                    <button class="profession-button active" data-profession="Firebrand">Firebrand</button>
                    <button class="profession-button" data-profession="Chronomancer">Chronomancer</button>
                    <button class="profession-button" data-profession="Scourge">Scourge</button>
                    <button class="profession-button" data-profession="Druid">Druid</button>
                    <button class="profession-button" data-profession="Condi Firebrand">Condi Firebrand</button>
                    <button class="profession-button" data-profession="Support Spb">Support Spb</button>
                </div>
                
                <div id="profession-info" class="profession-info"></div>
                <div class="search-container">
                    <input type="text" id="profession-search" class="search-input" placeholder="Search players or accounts...">
                    <button class="search-clear" onclick="clearSearch('profession')">&times;</button>
                </div>
                <div id="profession-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- Player Stats -->
            <div id="player-stats" class="tab-content">
                <h2>Player Stats</h2>
                <p class="description">Player activity and profession usage statistics (non-Glicko based).</p>
                
                <div class="metric-selector">
                    <button class="metric-button active" data-metric="Most Played Professions">Most Played Professions</button>
                </div>
                
                <div class="search-container">
                    <input type="text" id="player-stats-search" class="search-input" placeholder="Search players, professions, or accounts...">
                    <button class="search-clear" onclick="clearSearch('player-stats')">&times;</button>
                </div>
                <div id="player-stats-leaderboard" class="leaderboard-container"></div>
            </div>

            <!-- About -->
            <div id="about" class="tab-content">
                <h2>About the Rating System</h2>
                <div class="about-content">
                    <h3>🎯 Methodology</h3>
                    <p>This leaderboard uses a <strong>Glicko-2 rating system</strong> combined with session-based z-score evaluation to rank World vs World performance. Each player's skill is evaluated relative to their peers in the same combat sessions, ensuring fair comparisons across different battle contexts.</p>
                    
                    <h3>📊 How It Works</h3>
                    <ul>
                        <li><strong>Session-Based Evaluation:</strong> Each combat session is analyzed independently to calculate player rankings within that specific battle</li>
                        <li><strong>Z-Score Calculation:</strong> Player performance is normalized using z-scores: <code>(player_value - session_mean) / session_std</code></li>
                        <li><strong>Glicko-2 Rating:</strong> Dynamic rating system starting at 1500 that increases/decreases based on performance outcomes converted from z-scores</li>
                        <li><strong>Glicko Rating:</strong> Pure skill-based rating system that adapts based on wins/losses against other players (1200-1800+ typical range)</li>
                        <li><strong>Rating Deviation (RD):</strong> Measures uncertainty in a player's rating (starts at 350, decreases with more games)</li>
                    </ul>
                    
                    <h3>🏅 Leaderboard Types</h3>
                    <ul>
                        <li><strong>Individual Metrics:</strong> Rankings for specific performance areas (DPS, Healing, Barrier, Cleanses, Strips, Stability, Resistance, Might, Protection, Down Contribution, Burst Consistency, Distance to Tag)</li>
                        <li><strong>High Scores:</strong> Record-breaking single performance instances (highest burst damage, skill damage, single-fight DPS)</li>
                        <li><strong>Profession-Specific:</strong> Role-based rankings using weighted combinations of relevant metrics for each profession</li>
                        <li><strong>Time Filters:</strong> All-time, 30-day, 90-day, and 180-day rankings to show recent vs historical performance</li>
                        <li><strong>Player Summaries:</strong> Click any player name to view detailed performance breakdowns by profession and metric</li>
                    </ul>
                    
                    <h3>📈 Key Metrics Explained</h3>
                    <ul>
                        <li><strong>Rating:</strong> Glicko rating typically 1200-1800+ (higher = better skill level, used for ranking)</li>
                        <li><strong>Raids:</strong> Number of combat sessions analyzed (more sessions = lower uncertainty and participation bonus)</li>
                        <li><strong>Avg Rank:</strong> Average percentile rank in sessions (lower percentage = consistently better performance)</li>
                        <li><strong>Avg Stat:</strong> Average raw statistical value for the specific metric being ranked</li>
                        <li><strong>Rating Deviation:</strong> Uncertainty measure that decreases with more games played</li>
                    </ul>
                    
                    <h3>⚖️ Fairness Features</h3>
                    <ul>
                        <li><strong>Context-Aware:</strong> Performance evaluated relative to session participants, not absolute values</li>
                        <li><strong>Battle-Type Neutral:</strong> Works equally well for GvG fights, zerg battles, and keep sieges</li>
                        <li><strong>Fight Time Filtering:</strong> Players with ≥5 minutes participation are always included; ultra-short outliers (profession swaps, disconnects) are filtered to maintain data quality</li>
                        <li><strong>Experience Scaling:</strong> New players get reduced impact from extreme performances (1-2 games: 50%, 3-4 games: 75%, 5-8 games: 90%, 9+ games: full impact)</li>
                        <li><strong>Participation Rewards:</strong> 0-10% bonus for consistent participation encourages regular play without overwhelming skill</li>
                        <li><strong>Dynamic Filtering:</strong> Support metrics exclude low-outlier performances (25th percentile threshold) for meaningful comparisons</li>
                        <li><strong>Profession Recognition:</strong> Automatic detection of build variants (China DH, Boon Vindicator, etc.)</li>
                    </ul>
                </div>
            </div>
        </main>

        <!-- Player Detail Modal -->
        <div id="player-modal" class="modal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="player-modal-title">Player Details</h2>
                    <button class="modal-close" aria-label="Close modal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="player-summary-content">
                        <div class="player-overview">
                            <div class="player-info-card">
                                <h3>Overview</h3>
                                <div id="player-overview-content"></div>
                            </div>
                            <div class="player-activity-card">
                                <h3>Activity</h3>
                                <div id="player-activity-content"></div>
                            </div>
                        </div>
                        
                        <div class="player-metrics">
                            <h3>Performance Metrics</h3>
                            <div class="profession-filter" id="profession-filter" style="margin-bottom: 15px;">
                            </div>
                            <div id="player-metrics-content"></div>
                        </div>
                        
                        <div class="player-rating-history">
                            <h3>📈 Rating History</h3>
                            <div class="history-controls">
                                <div class="control-group">
                                    <label for="history-metric-select">Metric:</label>
                                    <select id="history-metric-select">
                                        <option value="DPS">DPS</option>
                                        <option value="Healing">Healing</option>
                                        <option value="Barrier">Barrier</option>
                                        <option value="Cleanses">Cleanses</option>
                                        <option value="Strips">Strips</option>
                                        <option value="Stability">Stability</option>
                                        <option value="Resistance">Resistance</option>
                                        <option value="Might">Might</option>
                                        <option value="Protection">Protection</option>
                                        <option value="Downs">Downs</option>
                                        <option value="Distance to Tag">Distance to Tag</option>
                                    </select>
                                </div>
                                <div class="control-group">
                                    <label for="history-profession-select">Profession:</label>
                                    <select id="history-profession-select">
                                        <option value="all">All Professions</option>
                                    </select>
                                </div>
                            </div>
                            <div class="chart-container">
                                <canvas id="rating-history-chart" width="400" height="250"></canvas>
                            </div>
                            <div id="chart-status" class="chart-status">Loading chart data...</div>
                        </div>
                        
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="script.js"></script>
</body>
</html>"""