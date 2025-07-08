"""
JavaScript functionality for GW2 WvW Leaderboards web UI.
"""

import json
from typing import Dict, Any

def get_javascript_content(data: Dict[str, Any]) -> str:
    """Return the complete JavaScript functionality for the web UI."""
    return f"""// Leaderboard data
const leaderboardData = {json.dumps(data, indent=2)};

// Current state
let currentFilter = '30d';
let currentTab = 'individual';
let currentMetric = 'DPS';
let currentProfession = 'Firebrand';
let currentHighScore = 'Highest 1 Sec Burst';
let currentPlayerStat = 'Most Played Professions';
let currentGuildFilter = 'all_players';
let showRatingDeltas = false;
let currentSort = {{ column: 'rank', direction: 'asc' }};
let chart;

// GW2 Wiki profession icons
const professionIcons = {{
    'Guardian': 'https://wiki.guildwars2.com/images/c/c7/Guardian_icon_small.png',
    'Dragonhunter': 'https://wiki.guildwars2.com/images/5/5d/Dragonhunter_icon_small.png',
    'China DH': 'https://wiki.guildwars2.com/images/5/5d/Dragonhunter_icon_small.png',
    'Firebrand': 'https://wiki.guildwars2.com/images/0/0e/Firebrand_icon_small.png',
    'Willbender': 'https://wiki.guildwars2.com/images/c/c7/Guardian_icon_small.png', // Fallback to Guardian
    'Warrior': 'https://wiki.guildwars2.com/images/4/45/Warrior_icon_small.png',
    'Berserker': 'https://wiki.guildwars2.com/images/a/a8/Berserker_icon_small.png',
    'Spellbreaker': 'https://wiki.guildwars2.com/images/0/08/Spellbreaker_icon_small.png',
    'Bladesworn': 'https://wiki.guildwars2.com/images/c/cf/Bladesworn_icon_small.png',
    'Engineer': 'https://wiki.guildwars2.com/images/0/07/Engineer_icon_small.png',
    'Scrapper': 'https://wiki.guildwars2.com/images/7/7d/Scrapper_icon_small.png',
    'Holosmith': 'https://wiki.guildwars2.com/images/a/aa/Holosmith_icon_small.png',
    'Mechanist': 'https://wiki.guildwars2.com/images/6/6d/Mechanist_icon_small.png',
    'Ranger': 'https://wiki.guildwars2.com/images/1/1e/Ranger_icon_small.npg',
    'Druid': 'https://wiki.guildwars2.com/images/9/9b/Druid_icon_small.png',
    'Soulbeast': 'https://wiki.guildwars2.com/images/f/f6/Soulbeast_icon_small.png',
    'Untamed': 'https://wiki.guildwars2.com/images/2/2d/Untamed_icon_small.png',
    'Thief': 'https://wiki.guildwars2.com/images/7/7a/Thief_icon_small.png',
    'Daredevil': 'https://wiki.guildwars2.com/images/f/f3/Daredevil_icon_small.png',
    'Deadeye': 'https://wiki.guildwars2.com/images/7/70/Deadeye_icon_small.png',
    'Specter': 'https://wiki.guildwars2.com/images/6/61/Specter_icon_small.png',
    'Elementalist': 'https://wiki.guildwars2.com/images/4/4e/Elementalist_icon_small.png',
    'Tempest': 'https://wiki.guildwars2.com/images/5/58/Tempest_icon_small.png',
    'Weaver': 'https://wiki.guildwars2.com/images/c/c3/Weaver_icon_small.png',
    'Catalyst': 'https://wiki.guildwars2.com/images/c/c5/Catalyst_icon_small.png',
    'Mesmer': 'https://wiki.guildwars2.com/images/7/79/Mesmer_icon_small.png',
    'Chronomancer': 'https://wiki.guildwars2.com/images/e/e0/Chronomancer_icon_small.png',
    'Mirage': 'https://wiki.guildwars2.com/images/c/c8/Mirage_icon_small.png',
    'Virtuoso': 'https://wiki.guildwars2.com/images/a/a7/Virtuoso_icon_small.png',
    'Necromancer': 'https://wiki.guildwars2.com/images/1/10/Necromancer_icon_small.png',
    'Reaper': 'https://wiki.guildwars2.com/images/9/93/Reaper_icon_small.png',
    'Scourge': 'https://wiki.guildwars2.com/images/e/e8/Scourge_icon_small.png',
    'Harbinger': 'https://wiki.guildwars2.com/images/1/1d/Harbinger_icon_small.png',
    'Revenant': 'https://wiki.guildwars2.com/images/4/4c/Revenant_icon_small.png',
    'Herald': 'https://wiki.guildwars2.com/images/3/39/Herald_icon_small.png',
    'Renegade': 'https://wiki.guildwars2.com/images/b/be/Renegade_icon_small.png',
    'Vindicator': 'https://wiki.guildwars2.com/images/6/6d/Vindicator_icon_small.png',
    'Condi Firebrand': 'https://wiki.guildwars2.com/images/0/0e/Firebrand_icon_small.png',
    'Support Spb': 'https://wiki.guildwars2.com/images/0/08/Spellbreaker_icon_small.png',
    'Boon Cata': 'https://wiki.guildwars2.com/images/c/c5/Catalyst_icon_small.png'
}};

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {{
    initializePage();
    setupEventListeners();
    loadCurrentData();
    
    // Make initial player names clickable after a short delay
    setTimeout(makePlayerNamesClickable, 100);
}});

function initializePage() {{
    // Set last updated time
    const lastUpdated = new Date(leaderboardData.generated_at);
    document.getElementById('lastUpdated').textContent = lastUpdated.toLocaleString();
    
    // Initialize dark mode from localStorage
    initializeDarkMode();
    
    // Initialize guild filtering if enabled
    if (leaderboardData.guild_enabled) {{
        const guildChips = document.getElementById('guild-chips');
        guildChips.style.display = 'flex';
        
        // Update guild member chip text
        const guildChip = document.getElementById('guild-chip');
        guildChip.textContent = `🛡️ ${{leaderboardData.guild_tag}}`;
    }}
}}

function initializeDarkMode() {{
    // Check for saved theme preference or default to light mode
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateToggleIcon(savedTheme);
}}

function toggleDarkMode() {{
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateToggleIcon(newTheme);
    
    // Reapply raids gradient with new theme colors
    setTimeout(() => applyRaidsGradient(), 50);
}}

function updateToggleIcon(theme) {{
    const toggleIcon = document.querySelector('.toggle-icon');
    if (theme === 'dark') {{
        toggleIcon.textContent = '☀️';
    }} else {{
        toggleIcon.textContent = '🌙';
    }}
}}

function setupEventListeners() {{
    // Dark mode toggle
    document.getElementById('darkModeToggle').addEventListener('click', toggleDarkMode);
    
    // Tab navigation
    document.querySelectorAll('.tab-button').forEach(button => {{
        button.addEventListener('click', function() {{
            switchTab(this.dataset.tab);
        }});
    }});
    
    // Modern segmented control for date filters
    document.querySelectorAll('input[name="time-filter"]').forEach(radio => {{
        radio.addEventListener('change', function() {{
            if (this.checked) {{
                selectDateFilter(this.value);
            }}
        }});
    }});
    
    // Metric selection - handle individual metrics and high scores separately
    document.querySelectorAll('#individual .metric-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectMetric(this.dataset.metric);
        }});
    }});
    
    // High score selection
    document.querySelectorAll('#high-scores .metric-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectHighScore(this.dataset.metric);
        }});
    }});
    
    // Player stats selection
    document.querySelectorAll('#player-stats .metric-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectPlayerStat(this.dataset.metric);
        }});
    }});
    
    // Profession selection
    document.querySelectorAll('.profession-button').forEach(button => {{
        button.addEventListener('click', function() {{
            selectProfession(this.dataset.profession);
        }});
    }});
    
    // Rating delta checkbox
    document.getElementById('show-rating-deltas').addEventListener('change', function() {{
        // Reload the current metric/tab to show/hide deltas
        const activeTab = document.querySelector('.tab-button.active').dataset.tab;
        if (activeTab === 'individual') {{
            const activeMetric = document.querySelector('#individual .metric-button.active').dataset.metric;
            loadIndividualMetric(activeMetric);
        }}
        // TODO: Add delta support for other tabs if needed
    }});
    
    // Modern chip-based guild filter selection
    document.querySelectorAll('.chip').forEach(chip => {{
        chip.addEventListener('click', function() {{
            // Remove active class from all chips
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            // Add active class to clicked chip
            this.classList.add('active');
            selectGuildFilter(this.dataset.guildFilter);
        }});
    }});
    
    // Search functionality
    const searchInputs = [
        {{
            id: 'individual-search',
            tableId: 'individual'
        }},
        {{
            id: 'high-scores-search',
            tableId: 'high-scores'
        }},
        {{
            id: 'profession-search',
            tableId: 'profession'
        }},
        {{
            id: 'player-stats-search',
            tableId: 'player-stats'
        }}
    ];
    
    searchInputs.forEach(search => {{
        const input = document.getElementById(search.id);
        if (input) {{
            let searchTimeout;
            
            input.addEventListener('input', function() {{
                const searchValue = this.value.trim();
                
                // Clear any existing timeout to debounce input
                clearTimeout(searchTimeout);
                
                // Set a small delay to avoid excessive filtering
                searchTimeout = setTimeout(() => {{
                    if (searchValue === '') {{
                        // If search is cleared, reload fresh data like clearSearch does
                        clearSearch(search.tableId);
                    }} else {{
                        // Otherwise filter the current data
                        filterTable(search.tableId, searchValue);
                    }}
                }}, 150); // 150ms delay
            }});
            
            input.addEventListener('keyup', function(e) {{
                const searchValue = this.value.trim();
                
                if (e.key === 'Enter') {{
                    // Clear any pending timeout on Enter key
                    clearTimeout(searchTimeout);
                    
                    if (searchValue === '') {{
                        clearSearch(search.tableId);
                    }} else {{
                        filterTable(search.tableId, searchValue);
                    }}
                }}
            }});
        }}
    }});
    
    // Modal event listeners
    const modal = document.getElementById('player-modal');
    const closeButton = modal.querySelector('.modal-close');
    
    // Close modal when clicking X
    closeButton.addEventListener('click', function() {{
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }});
    
    // Close modal when clicking outside
    modal.addEventListener('click', function(e) {{
        if (e.target === modal) {{
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }}
    }});
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape' && modal.style.display === 'flex') {{
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }}
    }});
}}

function selectDateFilter(filter) {{
    currentFilter = filter;
    // Radio buttons handle their own selection state
    loadCurrentData();
}}

function selectGuildFilter(guildFilter) {{
    currentGuildFilter = guildFilter;
    // Chips handle their own active state in the event listener
    loadCurrentData();
}}

function getCurrentData() {{
    return leaderboardData.date_filters[currentFilter];
}}

function getCurrentDateFilter() {{
    return currentFilter;
}}

function filterDataByGuildMembership(data) {{
    if (!leaderboardData.guild_enabled || currentGuildFilter === 'all_players') {{
        return data;
    }}
    
    // Filter to guild members only
    return data.filter(player => player.is_guild_member === true);
}}

function switchTab(tabName) {{
    currentTab = tabName;
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-tab="${{tabName}}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    
    loadCurrentData();
}}

function selectMetric(metric) {{
    currentMetric = metric;
    currentHighScore = metric;  // Also update high score selection
    document.querySelectorAll('.metric-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-metric="${{metric}}"]`).classList.add('active');
    if (currentTab === 'individual') {{
        loadIndividualMetric(metric);
    }} else if (currentTab === 'high-scores') {{
        loadHighScores(metric);
    }}
}}

function selectHighScore(metric) {{
    currentHighScore = metric;
    // For high scores tab, update the metric buttons in the high scores section
    if (currentTab === 'high-scores') {{
        document.querySelectorAll('#high-scores .metric-button').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`#high-scores [data-metric="${{metric}}"]`).classList.add('active');
        loadHighScores(metric);
    }}
}}

function selectProfession(profession) {{
    currentProfession = profession;
    document.querySelectorAll('.profession-button').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-profession="${{profession}}"]`).classList.add('active');
    if (currentTab === 'professions') {{
        loadProfessionLeaderboard(profession);
    }}
}}

function selectPlayerStat(metric) {{
    currentPlayerStat = metric;
    // For player stats tab, update the metric buttons in the player stats section
    if (currentTab === 'player-stats') {{
        document.querySelectorAll('#player-stats .metric-button').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`#player-stats [data-metric="${{metric}}"]`).classList.add('active');
        loadPlayerStats(metric);
    }}
}}

function loadCurrentData() {{
    switch(currentTab) {{
        case 'overall':
            loadOverallLeaderboard();
            break;
        case 'individual':
            loadIndividualMetric(currentMetric);
            break;
        case 'high-scores':
            loadHighScores(currentHighScore);
            break;
        case 'professions':
            loadProfessionLeaderboard(currentProfession);
            break;
        case 'player-stats':
            loadPlayerStats(currentPlayerStat);
            break;
    }}
}}

function loadOverallLeaderboard() {{
    const container = document.getElementById('overall-leaderboard');
    const rawData = getCurrentData().overall_leaderboard;
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(rawData);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    const columns = [
        {{
            key: 'rank',
            label: 'Rank',
            type: 'rank'
        }},
        {{
            key: 'account_name',
            label: 'Account',
            type: 'account'
        }},
        {{
            key: 'profession',
            label: 'Profession',
            type: 'profession'
        }},
        {{
            key: 'composite_score',
            label: 'Rating',
            type: 'number'
        }},
        {{
            key: 'games_played',
            label: 'Raids',
            type: 'raids'
        }},
        {{
            key: 'average_rank_percent',
            label: 'Avg Rank Per Raid',
            type: 'avg_rank'
        }}
    ];
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(3, 0, {{
            key: 'is_guild_member',
            label: 'Guild Member',
            type: 'guild_member'
        }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns);
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function loadIndividualMetric(metric) {{
    const container = document.getElementById('individual-leaderboard');
    const rawData = getCurrentData().individual_metrics[metric];
    
    if (!rawData) {{
        container.innerHTML = '<p>No data available for this metric.</p>';
        return;
    }}
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(rawData);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    const columns = [
        {{
            key: 'rank',
            label: 'Rank',
            type: 'rank'
        }},
        {{
            key: 'account_name',
            label: 'Account',
            type: 'account'
        }},
        {{
            key: 'profession',
            label: 'Profession',
            type: 'profession'
        }},
        {{
            key: 'composite_score',
            label: 'Rating',
            type: 'number'
        }},
        {{
            key: 'games_played',
            label: 'Raids',
            type: 'raids'
        }},
        {{
            key: 'average_rank_percent',
            label: 'Avg Rank',
            type: 'avg_rank'
        }},
        {{
            key: 'average_stat_value',
            label: `Avg ${{metric === 'Downs' ? 'DownCont' : metric}}`,
            type: 'stat'
        }}
    ];
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(3, 0, {{
            key: 'is_guild_member',
            label: 'Guild Member',
            type: 'guild_member'
        }});
    }}
    
    // Add delta column if checkbox is checked
    const showDeltas = document.getElementById('show-rating-deltas').checked;
    if (showDeltas) {{
        columns.splice(-1, 0, {{
            key: 'rating_delta',
            label: 'Change',
            type: 'rating_delta'
        }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns, 'individual');
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function loadProfessionLeaderboard(profession) {{
    const infoContainer = document.getElementById('profession-info');
    const container = document.getElementById('profession-leaderboard');
    const data = getCurrentData().profession_leaderboards[profession];
    
    if (!data) {{
        infoContainer.innerHTML = '<p>No data available for this profession.</p>';
        container.innerHTML = '';
        return;
    }}
    
    // Show profession info
    const metricsText = data.metrics.join(', ');
    const weightsText = data.weights.map(w => `${{(w * 100).toFixed(0)}}%`).join('/');
    
    infoContainer.innerHTML = `
        <h3>${{profession}} Metrics</h3>
        <p><strong>Weighted Metrics:</strong> ${{metricsText}}</p>
        <p><strong>Weights:</strong> ${{weightsText}}</p>
    `;
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(data.leaderboard);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    const columns = [
        {{
            key: 'rank',
            label: 'Rank',
            type: 'rank'
        }},
        {{
            key: 'account_name',
            label: 'Account',
            type: 'account'
        }},
        {{
            key: 'composite_score',
            label: 'Rating',
            type: 'number'
        }},
        {{
            key: 'games_played',
            label: 'Raids',
            type: 'raids'
        }},
        {{
            key: 'key_stats',
            label: 'Key Stats',
            type: 'stats'
        }},
        {{
            key: 'apm',
            label: 'APM',
            type: 'apm'
        }}
    ];
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(2, 0, {{
            key: 'is_guild_member',
            label: 'Guild Member',
            type: 'guild_member'
        }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns, 'profession');
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function loadHighScores(metric) {{
    const container = document.getElementById('high-scores-leaderboard');
    const rawData = getCurrentData().high_scores[metric];
    
    if (!rawData || rawData.length === 0) {{
        container.innerHTML = '<p>No high scores data available.</p>';
        return;
    }}
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(rawData);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    // Define columns based on metric type
    let columns;
    if (metric === 'Highest 1 Sec Burst') {{
        columns = [
            {{
                key: 'rank',
                label: 'Rank',
                type: 'rank'
            }},
            {{
                key: 'account_name',
                label: 'Account',
                type: 'account'
            }},
            {{
                key: 'profession',
                label: 'Profession',
                type: 'profession'
            }},
            {{
                key: 'burst_damage',
                label: 'Burst Damage',
                type: 'number'
            }},
            {{
                key: 'timestamp',
                label: 'Timestamp',
                type: 'stats'
            }}
        ];
    }} else if (metric === 'Highest Outgoing Skill Damage' || metric === 'Highest Incoming Skill Damage') {{
        columns = [
            {{
                key: 'rank',
                label: 'Rank',
                type: 'rank'
            }},
            {{
                key: 'player_name',
                label: 'Player',
                type: 'account'
            }},
            {{
                key: 'profession',
                label: 'Profession',
                type: 'profession'
            }},
            {{
                key: 'skill_name',
                label: 'Skill',
                type: 'stats'
            }},
            {{
                key: 'score_value',
                label: 'Damage',
                type: 'number'
            }},
            {{
                key: 'timestamp',
                label: 'Timestamp',
                type: 'stats'
            }}
        ];
    }} else if (metric === 'Highest Single Fight DPS') {{
        columns = [
            {{
                key: 'rank',
                label: 'Rank',
                type: 'rank'
            }},
            {{
                key: 'player_name',
                label: 'Player',
                type: 'account'
            }},
            {{
                key: 'profession',
                label: 'Profession',
                type: 'profession'
            }},
            {{
                key: 'score_value',
                label: 'DPS',
                type: 'number'
            }},
            {{
                key: 'fight_number',
                label: 'Fight',
                type: 'stats'
            }},
            {{
                key: 'timestamp',
                label: 'Timestamp',
                type: 'stats'
            }}
        ];
    }} else {{
        // Default columns for any other metrics
        columns = [
            {{
                key: 'rank',
                label: 'Rank',
                type: 'rank'
            }},
            {{
                key: 'account_name',
                label: 'Account',
                type: 'account'
            }},
            {{
                key: 'profession',
                label: 'Profession',
                type: 'profession'
            }},
            {{
                key: 'score_value',
                label: 'Score',
                type: 'number'
            }},
            {{
                key: 'timestamp',
                label: 'Timestamp',
                type: 'stats'
            }}
        ];
    }}
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(3, 0, {{
            key: 'is_guild_member',
            label: 'Guild Member',
            type: 'guild_member'
        }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns, 'high-scores');
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function loadPlayerStats(metric) {{
    const container = document.getElementById('player-stats-leaderboard');
    const rawData = getCurrentData().player_stats[metric];
    
    if (!rawData || rawData.length === 0) {{
        container.innerHTML = '<p>No player stats data available.</p>';
        return;
    }}
    
    // Filter data based on guild membership
    const filteredData = filterDataByGuildMembership(rawData);
    
    // Reassign ranks after filtering
    const dataWithNewRanks = filteredData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    // Define columns based on metric type
    let columns;
    if (metric === 'Most Played Professions') {{
        columns = [
            {{
                key: 'rank',
                label: 'Rank',
                type: 'rank'
            }},
            {{
                key: 'account_name',
                label: 'Account',
                type: 'account'
            }},
            {{
                key: 'primary_profession',
                label: 'Primary',
                type: 'profession'
            }},
            {{
                key: 'professions_played',
                label: 'Professions Played',
                type: 'profession_bar'
            }},
            {{
                key: 'total_sessions',
                label: 'Total Sessions',
                type: 'number'
            }},
            {{
                key: 'profession_count',
                label: 'Prof Count',
                type: 'number'
            }}
        ];
    }} else {{
        // Default columns for any other metrics
        columns = [
            {{
                key: 'rank',
                label: 'Rank',
                type: 'rank'
            }},
            {{
                key: 'account_name',
                label: 'Account',
                type: 'account'
            }},
            {{
                key: 'score_value',
                label: 'Score',
                type: 'number'
            }}
        ];
    }}
    
    // Add guild member column if guild filtering is enabled and we're showing all players
    if (leaderboardData.guild_enabled && currentGuildFilter === 'all_players') {{
        columns.splice(3, 0, {{
            key: 'is_guild_member',
            label: 'Guild Member',
            type: 'guild_member'
        }});
    }}
    
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns, 'player-stats');
    
    // Make player names clickable after updating the table
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function createLeaderboardTable(data, columns, tableId = 'leaderboard') {{
    if (!data || data.length === 0) {{
        return '<p>No data available.</p>';
    }}
    
    let html = `<table class="leaderboard-table" id="${{tableId}}-table"><thead><tr>`;
    
    columns.forEach((col, index) => {{
        html += `<th class="sortable" data-column="${{col.key}}" data-type="${{col.type}}" onclick="sortTable('${{tableId}}', '${{col.key}}', '${{col.type}}')">${{col.label}}</th>`;
    }});
    
    html += '</tr></thead><tbody>';
    
    data.forEach(row => {{
        html += '<tr>';
        columns.forEach(col => {{
            const value = row[col.key];
            html += `<td class="${{col.type}}-cell">${{formatCellValue(value, col.type)}}</td>`;
        }});
        html += '</tr>';
    }});
    
    html += '</tbody></table>';
    
    // Store original data for filtering and sorting
    window[`${{tableId}}_originalData`] = data;
    window[`${{tableId}}_columns`] = columns;
    window[`${{tableId}}_currentSort`] = {{
        column: null,
        direction: 'asc'
    }};
    
    // Apply raids gradient coloring after table creation
    setTimeout(() => {{
        applyRaidsGradient();
        updateSearchStats(tableId, data.length, data.length);
    }}, 10);
    
    return html;
}}

function formatCellValue(value, type) {{
    if ((value === null || value === undefined) && type !== 'apm') {{
        return 'N/A';
    }}
    
    switch (type) {{
        case 'rank':
            return `<span class="rank-cell">#${{value}}</span>`;
        case 'account':
            return `<span class="account-cell">${{value}}</span>`;
        case 'profession':
            const iconUrl = professionIcons[value] || '';
            const iconHtml = iconUrl ? `<img src="${{iconUrl}}" class="profession-icon" alt="${{value}}" onerror="this.style.display='none'">` : '';
            return `${{iconHtml}} ${{value}}`;
        case 'number':
            return Math.round(value);
        case 'raids':
            return `<span class="raids-value" data-raids="${{value}}">${{Math.round(value)}}</span>`;
        case 'percent':
            const percentClass = value < 25 ? 'rank-percent' : value > 75 ? 'rank-percent poor' : 'rank-percent average';
            return `<span class="${{percentClass}}">${{value.toFixed(1)}}%</span>`;
        case 'avg_rank':
            // Display actual average rank with 1 decimal place
            // Good ranks are low numbers (1-5), poor ranks are high numbers (10+)
            const rankClass = value <= 5 ? 'rank-percent' : value >= 10 ? 'rank-percent poor' : 'rank-percent average';
            return `<span class="${{rankClass}}">${{value.toFixed(1)}}</span>`;
        case 'stat':
            return `<span class="stat-value">${{value.toFixed(1)}}</span>`;
        case 'stats':
            return `<span class="stat-value">${{value}}</span>`;
        case 'guild_member':
            return value ? '<span class="guild-yes">✓ Yes</span>' : '<span class="guild-no">✗ No</span>';
        case 'rating_delta':
            if (Math.abs(value) < 0.1) {{
                return `<span class="delta-neutral">0.0</span>`;
            }} else if (value > 0) {{
                return `<span class="delta-positive">+${{value.toFixed(1)}}</span>`;
            }} else {{
                return `<span class="delta-negative">${{value.toFixed(1)}}</span>`;
            }}
        case 'apm':
            return (value !== null && value !== undefined) ? `<span class="stat-value">${{value}}</span>` : '<span class="stat-value">-</span>';
        case 'profession_bar':
            return formatProfessionBar(value);
        default:
            return value;
    }}
}}

function getProfessionColor(profession) {{
    // GW2 profession colors with more distinct variants for elite specs
    const professionColors = {{
        // Guardian (blue variations)
        'Guardian': '#72C1D9',      // Medium (base)
        'Dragonhunter': '#95D4E6',  // Lighter
        'Firebrand': '#4CABC7',     // Darker
        'Willbender': '#87CDDF',    // Light variant
        
        // Revenant (red variations)
        'Revenant': '#D16E5A',      // Medium (base)
        'Herald': '#E08A7A',        // Lighter
        'Renegade': '#BD4E37',      // Darker
        'Vindicator': '#D8796A',    // Light variant
        
        // Warrior (yellow variations)
        'Warrior': '#FFD166',       // Medium (base)
        'Berserker': '#FFDD99',     // Lighter
        'Spellbreaker': '#FFC233',  // Darker
        'Bladesworn': '#FFD680',    // Light variant
        
        // Engineer (orange variations)
        'Engineer': '#D09C59',      // Medium (base)
        'Scrapper': '#E3B585',      // Lighter
        'Holosmith': '#B7822D',     // Darker
        'Mechanist': '#D6A66F',     // Light variant
        
        // Ranger (green variations)
        'Ranger': '#8CDC82',        // Medium (base)
        'Druid': '#B5EAB0',         // Lighter
        'Soulbeast': '#64CC54',     // Darker
        'Untamed': '#9DE395',       // Light variant
        
        // Thief (pink variations)
        'Thief': '#C08F95',         // Medium (base)
        'Daredevil': '#D6AFBA',     // Lighter
        'Deadeye': '#A9696F',       // Darker
        'Specter': '#C79CA5',       // Light variant
        
        // Elementalist (red variations)
        'Elementalist': '#F68A87',  // Medium (base)
        'Tempest': '#FAB0AE',       // Lighter
        'Weaver': '#F25E5B',        // Darker
        'Catalyst': '#F79A97',      // Light variant
        
        // Mesmer (purple variations)
        'Mesmer': '#B679D5',        // Medium (base)
        'Chronomancer': '#D0A0E6',  // Lighter
        'Mirage': '#9952C4',        // Darker
        'Virtuoso': '#C288DB',      // Light variant
        
        // Necromancer (green variations)
        'Necromancer': '#52A76F',   // Medium (base)
        'Reaper': '#7BC498',        // Lighter
        'Scourge': '#2E8A46',       // Darker
        'Harbinger': '#62B17F',     // Light variant
        
        // Special cases (distinct variations)
        'Condi Firebrand': '#5CB0C9',  // Darker than Firebrand
        'Support Spb': '#FFB820',      // Darker than Spellbreaker
        'China DH': '#9BD8E8',         // Between Guardian and Dragonhunter
        'Boon Vindi': '#E18B7C'        // Between Revenant and Vindicator
    }};
    
    return professionColors[profession] || '#95a5a6';
}}

function formatProfessionBar(professions) {{
    if (!professions || professions.length === 0) {{
        return '<span class="stat-value">-</span>';
    }}
    
    const maxVisible = 4;
    const visibleProfessions = professions.slice(0, maxVisible);
    const remainingCount = professions.length - maxVisible;
    
    // Find max sessions for width scaling
    const maxSessions = Math.max(...visibleProfessions.map(prof => prof.session_count));
    
    let html = '<div class="profession-horizontal-container">';
    
    // Add horizontal bars for each profession
    visibleProfessions.forEach(prof => {{
        const widthPercentage = (prof.session_count / maxSessions) * 100;
        const color = getProfessionColor(prof.profession);
        const title = `${{prof.profession}}: ${{prof.session_count}} sessions`;
        
        html += `<div class="profession-bar-row">
                    <div class="profession-bar-label">${{prof.profession}}</div>
                    <div class="profession-bar-track">
                        <div class="profession-bar-fill" 
                             style="width: ${{widthPercentage}}%; background-color: ${{color}};" 
                             title="${{title}}"
                             data-profession="${{prof.profession}}"
                             data-count="${{prof.session_count}}">
                        </div>
                    </div>
                    <div class="profession-bar-count">${{prof.session_count}}</div>
                 </div>`;
    }});
    
    if (remainingCount > 0) {{
        html += `<div class="profession-more-text">and ${{remainingCount}} more</div>`;
    }}
    
    html += '</div>';
    
    return html;
}}

function applyRaidsGradient() {{
    const raidsElements = document.querySelectorAll('.raids-value');
    if (raidsElements.length === 0) return;
    
    // Get all raids values and find min/max
    const raidsValues = Array.from(raidsElements).map(el => parseInt(el.dataset.raids));
    const minRaids = Math.min(...raidsValues);
    const maxRaids = Math.max(...raidsValues);
    
    // Check if we're in dark mode
    const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
    
    // Apply gradient coloring
    raidsElements.forEach(element => {{
        const raids = parseInt(element.dataset.raids);
        const ratio = maxRaids === minRaids ? 0.5 : (raids - minRaids) / (maxRaids - minRaids);
        
        if (isDarkMode) {{
            // Dark mode: use brighter, more visible colors
            const red = Math.round(255 * (1 - ratio));
            const green = Math.round(255 * ratio);
            const blue = 50; // Add slight blue tint for better visibility
            
            element.style.backgroundColor = `rgba(${{red}}, ${{green}}, ${{blue}}, 0.4)`;
            element.style.color = ratio > 0.5 ? '#90ee90' : '#ffb3b3'; // Light green/red text
        }} else {{
            // Light mode: original colors
            const red = Math.round(255 * (1 - ratio));
            const green = Math.round(255 * ratio);
            const blue = 0;
            
            element.style.backgroundColor = `rgba(${{red}}, ${{green}}, ${{blue}}, 0.3)`;
            element.style.color = ratio > 0.5 ? '#2d5a2d' : '#5a2d2d'; // Dark green/red text
        }}
    }});
}}

// Sorting and Search Functions
function sortTable(tableId, column, type) {{
    const data = window[`${{tableId}}_originalData`];
    const columns = window[`${{tableId}}_columns`];
    const currentSort = window[`${{tableId}}_currentSort`];
    
    if (!data || !columns) return;
    
    // Determine sort direction
    let direction = 'asc';
    if (currentSort.column === column && currentSort.direction === 'asc') {{
        direction = 'desc';
    }}
    
    // Sort the data
    const sortedData = [...data].sort((a, b) => {{
        let valueA = a[column];
        let valueB = b[column];
        
        // Handle different data types
        if (type === 'number' || type === 'raids' || type === 'rank' || type === 'stat' || type === 'avg_rank') {{
            valueA = parseFloat(valueA) || 0;
            valueB = parseFloat(valueB) || 0;
        }} else if (type === 'percent') {{
            valueA = parseFloat(valueA) || 0;
            valueB = parseFloat(valueB) || 0;
        }} else {{
            // String comparison
            valueA = String(valueA || '').toLowerCase();
            valueB = String(valueB || '').toLowerCase();
        }}
        
        if (direction === 'asc') {{
            return valueA < valueB ? -1 : valueA > valueB ? 1 : 0;
        }} else {{
            return valueA > valueB ? -1 : valueA < valueB ? 1 : 0;
        }}
    }});
    
    // Reassign ranks after sorting
    const dataWithNewRanks = sortedData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    // Update the table
    const container = document.getElementById(`${{tableId}}-leaderboard`);
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns, tableId);
    
    // Update sort indicators
    updateSortIndicators(tableId, column, direction);
    
    // Store current sort state
    window[`${{tableId}}_currentSort`] = {{
        column,
        direction
    }};
    
    // Reapply search if active
    const searchInput = document.getElementById(`${{tableId}}-search`);
    if (searchInput && searchInput.value.trim()) {{
        filterTable(tableId, searchInput.value);
    }}
    
    // Make player names clickable again
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function updateSortIndicators(tableId, activeColumn, direction) {{
    const table = document.getElementById(`${{tableId}}-table`);
    if (!table) return;
    
    // Remove all sort classes
    const headers = table.querySelectorAll('th');
    headers.forEach(th => {{
        th.classList.remove('sort-asc', 'sort-desc');
    }});
    
    // Add sort class to active column
    const activeHeader = table.querySelector(`th[data-column="${{activeColumn}}"]`);
    if (activeHeader) {{
        activeHeader.classList.add(`sort-${{direction}}`);
    }}
}}

function filterTable(tableId, searchTerm) {{
    const originalData = window[`${{tableId}}_originalData`];
    const columns = window[`${{tableId}}_columns`];
    const currentSort = window[`${{tableId}}_currentSort`];
    
    if (!originalData || !columns) return;
    
    const term = searchTerm.toLowerCase().trim();
    let workingData = originalData;
    
    if (term) {{
        // Filter data based on search term
        workingData = originalData.filter(player => {{
            return (
                (player.account_name && player.account_name.toLowerCase().includes(term)) ||
                (player.player_name && player.player_name.toLowerCase().includes(term)) ||
                (player.profession && player.profession.toLowerCase().includes(term)) ||
                (player.primary_profession && player.primary_profession.toLowerCase().includes(term)) ||
                (player.professions_played && player.professions_played.toLowerCase().includes(term)) ||
                (player.skill_name && player.skill_name.toLowerCase().includes(term))
            );
        }});
    }}
    
    // Apply current sort if any
    if (currentSort && currentSort.column) {{
        const {{
            column,
            direction
        }} = currentSort;
        const sortType = columns.find(col => col.key === column)?.type || 'string';
        
        workingData = [...workingData].sort((a, b) => {{
            let valueA = a[column];
            let valueB = b[column];
            
            // Handle different data types
            if (sortType === 'number' || sortType === 'raids' || sortType === 'rank' || sortType === 'stat' || sortType === 'avg_rank') {{
                valueA = parseFloat(valueA) || 0;
                valueB = parseFloat(valueB) || 0;
            }} else if (sortType === 'percent') {{
                valueA = parseFloat(valueA) || 0;
                valueB = parseFloat(valueB) || 0;
            }} else {{
                // String comparison
                valueA = String(valueA || '').toLowerCase();
                valueB = String(valueB || '').toLowerCase();
            }}
            
            if (direction === 'asc') {{
                return valueA < valueB ? -1 : valueA > valueB ? 1 : 0;
            }} else {{
                return valueA > valueB ? -1 : valueA < valueB ? 1 : 0;
            }}
        }});
    }}
    
    // Reassign ranks for final data
    const dataWithNewRanks = workingData.map((player, index) => ({{
        ...player,
        rank: index + 1
    }}));
    
    // Update the table
    const container = document.getElementById(`${{tableId}}-leaderboard`);
    container.innerHTML = createLeaderboardTable(dataWithNewRanks, columns, tableId);
    
    // Update search stats
    updateSearchStats(tableId, dataWithNewRanks.length, originalData.length);
    
    // Make player names clickable again
    setTimeout(() => makePlayerNamesClickable(), 10);
}}

function clearSearch(tableId) {{
    const searchInput = document.getElementById(`${{tableId}}-search`);
    if (searchInput) {{
        searchInput.value = '';
    }}
    
    // Reload the current data fresh
    loadCurrentData();
}}

function updateSearchStats(tableId, filteredCount, totalCount) {{
    // This function can be called to show search result statistics
    // Implementation depends on UI requirements
}}

function makePlayerNamesClickable() {{
    // Find all account cells and make them clickable to show player modal
    const accountCells = document.querySelectorAll('.account-cell');
    accountCells.forEach(cell => {{
        if (!cell.classList.contains('clickable-setup')) {{
            cell.classList.add('clickable-setup');
            cell.style.cursor = 'pointer';
            cell.style.color = '#667eea';
            cell.addEventListener('click', function() {{
                const accountName = this.textContent.trim();
                showPlayerModal(accountName);
            }});
        }}
    }});
}}

function showPlayerModal(accountName) {{
    console.log('Show player modal for:', accountName);
    
    // Extract player data from all leaderboard data
    const playerData = extractPlayerData(accountName);
    
    if (!playerData || playerData.length === 0) {{
        console.log('No data found for player:', accountName);
        return;
    }}
    
    // Populate modal with player data
    populatePlayerModal(accountName, playerData);
    
    // Show the modal
    const modal = document.getElementById('player-modal');
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
}}

function extractPlayerData(accountName) {{
    const playerData = [];
    
    // Get data from current view
    const data = leaderboardData.date_filters[currentFilter];
    
    // Extract from individual metrics
    if (data.individual_metrics) {{
        Object.keys(data.individual_metrics).forEach(metric => {{
            const metricData = data.individual_metrics[metric];
            const playerEntries = metricData.filter(entry => entry.account_name === accountName);
            playerEntries.forEach(entry => {{
                playerData.push({{
                    ...entry,
                    metric: metric,
                    category: 'individual'
                }});
            }});
        }});
    }}
    
    // Extract from profession leaderboards
    if (data.profession_leaderboards) {{
        Object.keys(data.profession_leaderboards).forEach(profession => {{
            const profData = data.profession_leaderboards[profession];
            // Handle both 'leaderboard' and 'players' keys for backward compatibility
            const playersList = profData.leaderboard || profData.players;
            if (playersList) {{
                const playerEntries = playersList.filter(entry => entry.account_name === accountName);
                playerEntries.forEach(entry => {{
                    playerData.push({{
                        ...entry,
                        profession: profession,
                        category: 'profession'
                    }});
                }});
            }}
        }});
    }}
    
    // Extract from player stats
    if (data.player_stats && data.player_stats['Most Played Professions']) {{
        const playerStats = data.player_stats['Most Played Professions'].filter(entry => entry.account_name === accountName);
        playerStats.forEach(entry => {{
            playerData.push({{
                ...entry,
                category: 'stats'
            }});
        }});
    }}
    
    return playerData;
}}

function populatePlayerModal(accountName, playerData) {{
    // Set modal title
    document.getElementById('player-modal-title').textContent = `Player Details: ${{accountName}}`;
    
    // Populate overview section
    populatePlayerOverview(accountName, playerData);
    
    // Populate activity section
    populatePlayerActivity(playerData);
    
    // Populate metrics section
    populatePlayerMetrics(playerData);
    
    // Set up profession filter
    setupProfessionFilter(playerData);
    
    // Set up rating history chart
    setupRatingHistoryChart(accountName, playerData);
}}

function populatePlayerOverview(accountName, playerData) {{
    const overviewContent = document.getElementById('player-overview-content');
    
    // Get unique professions
    const professions = [...new Set(playerData.map(entry => entry.profession).filter(Boolean))];
    
    // Calculate total games played
    const totalGames = playerData.reduce((sum, entry) => sum + (entry.games_played || 0), 0);
    
    // Get guild status
    const isGuildMember = playerData.some(entry => entry.is_guild_member);
    const guildStatus = isGuildMember ? `✅ Guild Member` : `❌ Not in Guild`;
    
    overviewContent.innerHTML = `
        <div class="stat-row">
            <span class="stat-label">Account:</span>
            <span class="stat-value">${{accountName}}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Guild Status:</span>
            <span class="stat-value">${{guildStatus}}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Professions Played:</span>
            <span class="stat-value">${{professions.length}}</span>
        </div>
        <div class="stat-row">
            <span class="stat-label">Total Games:</span>
            <span class="stat-value">${{totalGames}}</span>
        </div>
    `;
}}

function populatePlayerActivity(playerData) {{
    const activityContent = document.getElementById('player-activity-content');
    
    // Get profession activity stats
    const professionStats = {{}};
    playerData.forEach(entry => {{
        if (entry.profession && entry.games_played) {{
            if (!professionStats[entry.profession]) {{
                professionStats[entry.profession] = 0;
            }}
            professionStats[entry.profession] += entry.games_played;
        }}
    }});
    
    // Sort by games played
    const sortedProfessions = Object.entries(professionStats)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);
    
    let activityHTML = '<div class="activity-list">';
    sortedProfessions.forEach(([profession, games]) => {{
        activityHTML += `
            <div class="activity-item">
                <span class="activity-profession">${{profession}}</span>
                <span class="activity-games">${{games}} games</span>
            </div>
        `;
    }});
    activityHTML += '</div>';
    
    activityContent.innerHTML = activityHTML;
}}

function populatePlayerMetrics(playerData) {{
    const metricsContent = document.getElementById('player-metrics-content');
    
    // Group by category and metric
    const individualMetrics = playerData.filter(entry => entry.category === 'individual');
    const professionMetrics = playerData.filter(entry => entry.category === 'profession');
    
    let metricsHTML = '<div class="metric-grid">';
    
    // Individual metrics
    if (individualMetrics.length > 0) {{
        metricsHTML += '<h4>Individual Metrics</h4>';
        individualMetrics.forEach(entry => {{
            metricsHTML += `
                <div class="metric-item">
                    <div class="metric-name">${{entry.metric}} (${{entry.profession}})</div>
                    <div class="metric-value">
                        <div>Rating: ${{entry.glicko_rating ? entry.glicko_rating.toFixed(1) : 'N/A'}}</div>
                        <div>Rank: #${{entry.rank || 'N/A'}}</div>
                        <div>Games: ${{entry.games_played || 0}}</div>
                    </div>
                </div>
            `;
        }});
    }}
    
    // Profession metrics
    if (professionMetrics.length > 0) {{
        metricsHTML += '<h4>Profession Rankings</h4>';
        professionMetrics.forEach(entry => {{
            metricsHTML += `
                <div class="metric-item">
                    <div class="metric-name">${{entry.profession}}</div>
                    <div class="metric-value">
                        <div>Rating: ${{entry.glicko_rating ? entry.glicko_rating.toFixed(1) : 'N/A'}}</div>
                        <div>Rank: #${{entry.rank || 'N/A'}}</div>
                        <div>Games: ${{entry.games_played || 0}}</div>
                    </div>
                </div>
            `;
        }});
    }}
    
    metricsHTML += '</div>';
    metricsContent.innerHTML = metricsHTML;
}}

function setupProfessionFilter(playerData) {{
    const professionFilter = document.getElementById('profession-filter');
    const professions = [...new Set(playerData.map(entry => entry.profession).filter(Boolean))];
    
    let filterHTML = '<div class="filter-chips">';
    filterHTML += '<div class="chip active" data-profession="all">All</div>';
    professions.forEach(profession => {{
        filterHTML += `<div class="chip" data-profession="${{profession}}">${{profession}}</div>`;
    }});
    filterHTML += '</div>';
    
    professionFilter.innerHTML = filterHTML;
    
    // Add click handlers
    professionFilter.querySelectorAll('.chip').forEach(chip => {{
        chip.addEventListener('click', function() {{
            // Remove active class from all chips
            professionFilter.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            // Add active class to clicked chip
            this.classList.add('active');
            
            // Filter metrics display
            const selectedProfession = this.dataset.profession;
            filterMetricsByProfession(selectedProfession, playerData);
        }});
    }});
}}

function filterMetricsByProfession(profession, playerData) {{
    // Re-populate metrics with filtered data
    const filteredData = profession === 'all' 
        ? playerData 
        : playerData.filter(entry => entry.profession === profession);
    
    populatePlayerMetrics(filteredData);
}}

function setupRatingHistoryChart(accountName, playerData) {{
    try {{
        const canvas = document.getElementById('rating-history-chart');
        const chartStatus = document.getElementById('chart-status');
        const metricSelect = document.getElementById('history-metric-select');
        const professionSelect = document.getElementById('history-profession-select');
        
        if (!canvas || !chartStatus || !metricSelect || !professionSelect) {{
            console.error('Missing chart elements');
            return;
        }}
        
        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {{
            chartStatus.textContent = 'Chart.js library not loaded. Rating history unavailable.';
            console.error('Chart.js not available');
            return;
        }}
        
        const ctx = canvas.getContext('2d');
        
        // Populate profession dropdown with only professions that have individual metric data
        const professions = [...new Set(playerData
            .filter(entry => entry.category === 'individual')
            .map(entry => entry.profession)
            .filter(Boolean)
        )];
        
        professionSelect.innerHTML = '';
        if (professions.length === 0) {{
            professionSelect.innerHTML = '<option value="">No profession data available</option>';
            chartStatus.textContent = 'No individual metric data found for rating history.';
            return;
        }}
        
        professions.forEach(profession => {{
            const option = document.createElement('option');
            option.value = profession;
            option.textContent = profession;
            professionSelect.appendChild(option);
        }});
        
        // Set first profession as default
        professionSelect.value = professions[0];
    
    let currentChart = null;
    
    async function fetchRatingHistory(accountName, metric, profession) {{
        // In a real implementation, this would call a backend API
        // For now, simulate historical data based on current data
        const currentData = playerData.find(entry => 
            entry.category === 'individual' && 
            entry.metric === metric && 
            entry.profession === profession
        );
        
        if (!currentData) {{
            return [];
        }}
        
        // Simulate historical progression - create a realistic rating journey
        const currentRating = currentData.glicko_rating;
        const gamesPlayed = currentData.games_played || 1;
        const historyPoints = Math.min(gamesPlayed, 10); // Show up to 10 historical points
        
        const history = [];
        const startRating = 1500; // Default Glicko starting rating
        const ratingDiff = currentRating - startRating;
        
        for (let i = 0; i < historyPoints; i++) {{
            const progress = i / (historyPoints - 1);
            const rating = startRating + (ratingDiff * progress);
            
            // Create realistic timestamps (last 30 days)
            const daysAgo = (historyPoints - 1 - i) * 3;
            const timestamp = new Date();
            timestamp.setDate(timestamp.getDate() - daysAgo);
            
            history.push({{
                timestamp: timestamp.toISOString().split('T')[0], // YYYY-MM-DD format
                rating: rating + (Math.random() - 0.5) * 20 // Add some realistic variance
            }});
        }}
        
        return history;
    }}
    
    async function updateChart() {{
        const selectedMetric = metricSelect.value;
        const selectedProfession = professionSelect.value;
        
        if (!selectedProfession) {{
            chartStatus.textContent = 'Please select a profession.';
            return;
        }}
        
        chartStatus.textContent = 'Loading rating history...';
        
        try {{
            const historyData = await fetchRatingHistory(accountName, selectedMetric, selectedProfession);
            
            if (historyData.length === 0) {{
                chartStatus.textContent = 'No rating history available for this combination.';
                if (currentChart) {{
                    currentChart.destroy();
                    currentChart = null;
                }}
                return;
            }}
            
            // Prepare chart data
            const labels = historyData.map(point => point.timestamp);
            const ratings = historyData.map(point => point.rating);
            
            const chartData = {{
                labels: labels,
                datasets: [{{
                    label: `${{selectedMetric}} Rating (${{selectedProfession}})`,
                    data: ratings,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#667eea',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }}]
            }};
            
            // Get current theme for chart styling
            const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
            const textColor = isDarkMode ? '#ecf0f1' : '#333333';
            const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
            
            const config = {{
                type: 'line',
                data: chartData,
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top',
                            labels: {{
                                color: textColor,
                                font: {{
                                    size: 12
                                }}
                            }}
                        }},
                        title: {{
                            display: true,
                            text: `Rating History - ${{accountName}}`,
                            color: textColor,
                            font: {{
                                size: 16,
                                weight: 'bold'
                            }}
                        }},
                        tooltip: {{
                            mode: 'index',
                            intersect: false,
                            backgroundColor: isDarkMode ? 'rgba(44, 62, 80, 0.9)' : 'rgba(255, 255, 255, 0.9)',
                            titleColor: textColor,
                            bodyColor: textColor,
                            borderColor: '#667eea',
                            borderWidth: 1,
                            callbacks: {{
                                title: function(context) {{
                                    return 'Date: ' + context[0].label;
                                }},
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(1);
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: false,
                            title: {{
                                display: true,
                                text: 'Glicko Rating',
                                color: textColor,
                                font: {{
                                    size: 12,
                                    weight: 'bold'
                                }}
                            }},
                            ticks: {{
                                color: textColor,
                                font: {{
                                    size: 11
                                }}
                            }},
                            grid: {{
                                color: gridColor
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: 'Date',
                                color: textColor,
                                font: {{
                                    size: 12,
                                    weight: 'bold'
                                }}
                            }},
                            ticks: {{
                                color: textColor,
                                font: {{
                                    size: 11
                                }}
                            }},
                            grid: {{
                                color: gridColor
                            }}
                        }}
                    }},
                    interaction: {{
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }}
                }}
            }};
            
            // Destroy existing chart
            if (currentChart) {{
                currentChart.destroy();
            }}
            
            // Create new chart
            currentChart = new Chart(ctx, config);
            
            const currentRating = ratings[ratings.length - 1];
            const startRating = ratings[0];
            const change = currentRating - startRating;
            const changeText = change >= 0 ? `+${{change.toFixed(1)}}` : `${{change.toFixed(1)}}`;
            const changeColor = change >= 0 ? '#28a745' : '#dc3545';
            
            chartStatus.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>Current Rating: <strong>${{currentRating.toFixed(1)}}</strong></span>
                    <span style="color: ${{changeColor}};">Overall Change: <strong>${{changeText}}</strong></span>
                    <span>${{historyData.length}} data points</span>
                </div>
            `;
            
        }} catch (error) {{
            console.error('Error loading rating history:', error);
            chartStatus.textContent = 'Error loading rating history data.';
        }}
    }}
    
        // Set up event listeners
        metricSelect.addEventListener('change', updateChart);
        professionSelect.addEventListener('change', updateChart);
        
        // Initial chart load
        updateChart();
        
    }} catch (error) {{
        console.error('Error setting up rating history chart:', error);
        const chartStatus = document.getElementById('chart-status');
        if (chartStatus) {{
            chartStatus.textContent = 'Rating history chart unavailable due to error.';
        }}
    }}
}}

"""