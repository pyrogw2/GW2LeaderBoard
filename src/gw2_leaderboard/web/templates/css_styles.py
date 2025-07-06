"""
CSS styles for GW2 WvW Leaderboards web UI.
"""

def get_css_content() -> str:
    """Return the complete CSS styles for the web UI."""
    return """:root {
    --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --main-bg: #f8f9fa;
    --text-color: #333333;
    --text-color-secondary: #666666;
    --text-color-light: #ffffff;
    --card-bg: #ffffff;
    --border-color: #dee2e6;
    --hover-bg: #f8f9fa;
    --button-bg: rgba(255,255,255,0.2);
    --button-border: rgba(255,255,255,0.3);
    --button-hover: rgba(255,255,255,0.3);
    --button-active: rgba(255,255,255,0.4);
    --shadow: 0 10px 30px rgba(0,0,0,0.2);
}

[data-theme="dark"] {
    --bg-gradient: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
    --main-bg: #2c3e50;
    --text-color: #ecf0f1;
    --text-color-secondary: #bdc3c7;
    --text-color-light: #ffffff;
    --card-bg: #34495e;
    --border-color: #4a6741;
    --hover-bg: #3c5a99;
    --button-bg: rgba(255,255,255,0.1);
    --button-border: rgba(255,255,255,0.2);
    --button-hover: rgba(255,255,255,0.2);
    --button-active: rgba(255,255,255,0.3);
    --shadow: 0 10px 30px rgba(0,0,0,0.4);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background: var(--bg-gradient);
    min-height: 100vh;
    transition: all 0.3s ease;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    margin-bottom: 30px;
    color: var(--text-color-light);
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
}

.header-text {
    text-align: center;
    flex: 1;
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 10px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

.subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    margin-bottom: 10px;
}

.last-updated {
    font-size: 0.9rem;
    opacity: 0.8;
}

.dark-mode-toggle {
    background: var(--button-bg);
    border: 2px solid var(--button-border);
    border-radius: 50px;
    padding: 12px 16px;
    cursor: pointer;
    transition: all 0.3s ease;
    color: var(--text-color-light);
    font-size: 1.2rem;
    min-width: 60px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.dark-mode-toggle:hover {
    background: var(--button-hover);
    border-color: rgba(255,255,255,0.5);
    transform: scale(1.05);
}

.toggle-icon {
    transition: transform 0.3s ease;
    font-size: 1.2rem;
}

.nav-tabs {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
    background: var(--button-bg);
    border-radius: 10px;
    padding: 10px;
    backdrop-filter: blur(10px);
}

/* Modern Filters Layout */
.modern-filters {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-wrap: wrap;
    gap: 30px;
    margin-bottom: 20px;
    background: var(--button-bg);
    border-radius: 15px;
    padding: 12px 20px;
    backdrop-filter: blur(10px);
}

/* iOS-style Segmented Control */
.segmented-control {
    display: flex;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 3px;
    position: relative;
}

.segmented-control input[type="radio"] {
    display: none;
}

.segmented-control label {
    padding: 6px 16px;
    border-radius: 5px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: var(--text-color-light);
    font-weight: 500;
    font-size: 14px;
    text-align: center;
    min-width: 40px;
}

.segmented-control input[type="radio"]:checked + label {
    background: #4CAF50;
    color: white;
    box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
    font-weight: 600;
}

/* Modern Filter Chips */
.filter-chips {
    display: flex;
    gap: 8px;
}

.chip {
    padding: 6px 12px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-color-light);
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 14px;
    font-weight: 500;
    border: 1px solid transparent;
}

.chip:hover {
    background: rgba(255, 255, 255, 0.15);
}

.chip.active {
    background: var(--accent-color);
    color: white;
    border-color: var(--accent-color);
}

/* Modern Toggle Switch */
.delta-toggle {
    display: flex;
    align-items: center;
    gap: 10px;
}

.toggle-label {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-color-light);
}

.toggle-switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
}

.toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(255, 255, 255, 0.2);
    transition: 0.3s;
    border-radius: 24px;
}

.toggle-slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background: white;
    transition: 0.3s;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle-switch input:checked + .toggle-slider {
    background: #4CAF50;
}

.toggle-switch input:checked + .toggle-slider:before {
    transform: translateX(20px);
}

.delta-checkbox-label {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--text-color-light);
    font-weight: bold;
    cursor: pointer;
    font-size: 1rem;
}

.delta-checkbox {
    width: 18px;
    height: 18px;
    cursor: pointer;
}

.filter-label {
    color: var(--text-color-light);
    font-weight: bold;
    margin-right: 15px;
    font-size: 1rem;
}

.date-filter-button, .guild-filter-button {
    background: var(--button-bg);
    border: 2px solid var(--button-border);
    padding: 8px 16px;
    border-radius: 6px;
    color: var(--text-color-light);
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.date-filter-button:hover, .guild-filter-button:hover {
    background: var(--button-hover);
    border-color: rgba(255,255,255,0.5);
}

.date-filter-button.active, .guild-filter-button.active {
    background: var(--button-active);
    border-color: rgba(255,255,255,0.6);
    font-weight: bold;
}

.tab-button {
    background: transparent;
    border: none;
    padding: 12px 24px;
    margin: 0 5px;
    border-radius: 8px;
    color: var(--text-color-light);
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.tab-button:hover {
    background: var(--button-hover);
}

.tab-button.active {
    background: var(--button-active);
    font-weight: bold;
}

main {
    background: var(--main-bg);
    border-radius: 15px;
    padding: 30px;
    box-shadow: var(--shadow);
    min-height: 600px;
    transition: all 0.3s ease;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

h2 {
    color: var(--text-color);
    margin-bottom: 10px;
    font-size: 1.8rem;
}

.description {
    color: var(--text-color-secondary);
    margin-bottom: 25px;
    font-size: 1.1rem;
}

.metric-selector {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: 8px;
    margin-bottom: 25px;
    max-width: 1200px;
    margin-left: auto;
    margin-right: auto;
}

.profession-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 25px;
    justify-content: center;
}

.metric-button {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    padding: 6px 12px;
    border-radius: 16px;
    cursor: pointer;
    transition: all 0.2s ease;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--text-color);
    text-align: center;
    white-space: nowrap;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.profession-button {
    background: var(--card-bg);
    border: 2px solid var(--border-color);
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.9rem;
    color: var(--text-color);
}

.metric-button:hover {
    background: var(--hover-bg);
    border-color: var(--text-color-secondary);
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

.profession-button:hover {
    background: var(--hover-bg);
    border-color: var(--text-color-secondary);
}

.metric-button.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.profession-button.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

[data-theme="dark"] .metric-button {
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

[data-theme="dark"] .metric-button:hover {
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
}

[data-theme="dark"] .metric-button.active {
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.5);
}

.profession-info {
    background: var(--card-bg);
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
    border-left: 4px solid #667eea;
    border: 1px solid var(--border-color);
}

.profession-info h3 {
    margin-bottom: 10px;
    color: var(--text-color);
}

.profession-info p {
    color: var(--text-color-secondary);
    margin-bottom: 5px;
}

.leaderboard-container {
    overflow-x: auto;
}

.search-container {
    position: relative;
    margin-bottom: 15px;
    max-width: 400px;
}

.search-input {
    width: 100%;
    padding: 10px 40px 10px 15px;
    border: 2px solid var(--border-color);
    border-radius: 25px;
    background: var(--card-bg);
    color: var(--text-color);
    font-size: 14px;
    transition: all 0.3s ease;
    outline: none;
}

.search-input:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-input::placeholder {
    color: var(--text-color-secondary);
}

.search-clear {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    font-size: 18px;
    color: var(--text-color-secondary);
    cursor: pointer;
    padding: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.2s ease;
}

.search-clear:hover {
    color: var(--text-color);
}

.search-stats {
    margin-top: 5px;
    font-size: 12px;
    color: var(--text-color-secondary);
    text-align: right;
}

.leaderboard-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.leaderboard-table th,
.leaderboard-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
    color: var(--text-color);
}

.leaderboard-table th {
    background: var(--card-bg);
    font-weight: bold;
    color: var(--text-color);
    position: sticky;
    top: 0;
    border-bottom: 2px solid var(--border-color);
    cursor: pointer;
    user-select: none;
    position: relative;
    transition: background-color 0.2s ease;
}

.leaderboard-table th:hover {
    background: var(--hover-bg);
}

.leaderboard-table th.sortable {
    padding-right: 30px;
    min-width: 80px;
}

.leaderboard-table th.sortable::after {
    content: '↕';
    position: absolute;
    right: 8px;
    opacity: 0.5;
    font-size: 14px;
    line-height: 1;
}

.leaderboard-table th.sort-asc::after {
    content: '↑';
    opacity: 1;
    color: #667eea;
    font-weight: bold;
}

.leaderboard-table th.sort-desc::after {
    content: '↓';
    opacity: 1;
    color: #667eea;
    font-weight: bold;
}

.leaderboard-table tr:hover {
    background: var(--hover-bg);
}

.rank-cell {
    font-weight: bold;
    color: #667eea;
    width: 60px;
}

.account-cell {
    font-weight: 500;
    min-width: 200px;
}

.account-link {
    color: var(--text-color);
    text-decoration: none;
    transition: all 0.3s ease;
    border-radius: 4px;
    padding: 2px 4px;
}

.account-link:hover {
    color: #667eea;
    background: var(--hover-bg);
    text-decoration: none;
}

.profession-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
    text-transform: uppercase;
    margin-left: 10px;
    gap: 4px;
    white-space: nowrap;
}

.profession-icon {
    width: 16px;
    height: 16px;
    border-radius: 2px;
}

.stat-value {
    font-family: 'Courier New', monospace;
    font-weight: bold;
}

.rank-percent {
    color: #28a745;
    font-weight: bold;
}

.rank-percent.poor {
    color: #dc3545;
}

.rank-percent.average {
    color: #ffc107;
}

.raids-value {
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 3px;
}

.guild-yes {
    color: #28a745;
    font-weight: bold;
}

/* Profession bar styles */
.profession-horizontal-container {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 220px;
    font-size: 11px;
}

.profession-bar-row {
    display: flex;
    align-items: center;
    gap: 4px;
    height: 16px;
}

.profession-bar-label {
    min-width: 80px;
    font-size: 10px;
    color: #666;
    text-align: right;
    font-weight: 500;
    white-space: nowrap;
}

[data-theme="dark"] .profession-bar-label {
    color: #aaa;
}

.profession-bar-track {
    flex: 1;
    height: 12px;
    background-color: #f0f0f0;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #ddd;
}

[data-theme="dark"] .profession-bar-track {
    background-color: #444;
    border-color: #666;
}

.profession-bar-fill {
    height: 100%;
    cursor: pointer;
    transition: opacity 0.2s ease;
    min-width: 2px;
}

.profession-bar-fill:hover {
    opacity: 0.8;
}

.profession-bar-count {
    min-width: 20px;
    text-align: right;
    font-size: 10px;
    color: #666;
    font-weight: bold;
}

[data-theme="dark"] .profession-bar-count {
    color: #aaa;
}

.profession-more-text {
    font-size: 10px;
    color: #666;
    font-style: italic;
    margin-top: 2px;
    text-align: center;
}

[data-theme="dark"] .profession-more-text {
    color: #aaa;
}

.profession-text-summary {
    font-size: 0.85em;
    color: #6c757d;
    margin-top: 2px;
    line-height: 1.2;
}

[data-theme="dark"] .profession-text-summary {
    color: #adb5bd;
}

.profession-text {
    font-weight: 500;
}

.profession-more {
    color: #6c757d;
    font-style: italic;
}

[data-theme="dark"] .profession-more {
    color: #adb5bd;
}

.guild-no {
    color: #6c757d;
    font-weight: normal;
}

.delta-positive {
    color: #28a745;
    font-weight: bold;
}

.delta-negative {
    color: #dc3545;
    font-weight: bold;
}

.delta-neutral {
    color: #6c757d;
    font-weight: normal;
}

.about-content {
    line-height: 1.8;
}

.about-content h3 {
    color: #667eea;
    margin: 25px 0 15px 0;
    font-size: 1.3rem;
}

.about-content ul {
    margin-left: 20px;
    margin-bottom: 20px;
}

.about-content li {
    margin-bottom: 8px;
}

.about-content strong {
    color: var(--text-color);
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .header-content {
        flex-direction: column;
        text-align: center;
    }
    
    .dark-mode-toggle {
        align-self: center;
        margin-top: 10px;
    }
    
    header h1 {
        font-size: 2rem;
    }
    
    .nav-tabs {
        flex-wrap: wrap;
        gap: 5px;
    }
    
    .tab-button {
        padding: 10px 16px;
        font-size: 0.9rem;
    }
    
    main {
        padding: 20px;
    }
    
    .metric-selector {
        grid-template-columns: repeat(6, 1fr);
        gap: 6px;
    }
    
    .profession-selector {
        justify-content: flex-start;
    }
    
    .metric-button {
        padding: 5px 10px;
        font-size: 0.75rem;
    }
    
    .profession-button {
        padding: 8px 16px;
        font-size: 0.8rem;
    }
    
    .leaderboard-table th,
    .leaderboard-table td {
        padding: 8px;
        font-size: 0.9rem;
    }
    
    .account-cell {
        min-width: 150px;
    }
}

/* Player Detail Modal */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.7);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 0.3s ease;
}

.modal-content {
    background: var(--main-bg);
    border-radius: 15px;
    box-shadow: var(--shadow);
    max-width: 95vw;
    max-height: 90vh;
    width: 1200px;
    overflow: hidden;
    animation: slideIn 0.3s ease;
}

.modal-header {
    padding: 20px 30px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--hover-bg);
}

.modal-header h2 {
    margin: 0;
    color: var(--text-color);
    font-size: 1.5rem;
}

.modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: var(--text-color);
    cursor: pointer;
    padding: 5px;
    border-radius: 50%;
    width: 35px;
    height: 35px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s ease;
}

.modal-close:hover {
    background: var(--hover-bg);
}

.modal-body {
    padding: 30px;
    overflow-y: auto;
    max-height: calc(90vh - 100px);
}

.player-summary-content {
    display: flex;
    flex-direction: column;
    gap: 30px;
}

.player-overview {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.player-info-card, .player-activity-card {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 20px;
}

.player-info-card h3, .player-activity-card h3, 
.player-metrics h3, .player-professions h3, .player-sessions h3, .player-rating-history h3 {
    margin: 0 0 15px 0;
    color: #667eea;
    font-size: 1.2rem;
    border-bottom: 2px solid #667eea;
    padding-bottom: 5px;
}

.player-metrics, .player-professions, .player-sessions, .player-rating-history {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 20px;
    margin-top: 20px;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
}

.metric-item {
    background: var(--hover-bg);
    padding: 15px;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}

.metric-name {
    font-weight: bold;
    color: var(--text-color);
    margin-bottom: 5px;
}

.metric-value {
    color: var(--text-color-secondary);
    font-size: 0.9rem;
}

.profession-tabs {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.profession-tab {
    background: var(--button-bg);
    border: 1px solid var(--button-border);
    padding: 8px 16px;
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: var(--text-color);
}

.profession-tab:hover {
    background: var(--button-hover);
}

.profession-tab.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

/* Rating History Chart Styles */
.history-controls {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.control-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.control-group label {
    font-weight: 500;
    color: var(--text-color);
    font-size: 0.9rem;
}

.control-group select {
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    border-radius: 5px;
    background: var(--card-bg);
    color: var(--text-color);
    font-size: 0.9rem;
    min-width: 150px;
}

.control-group select:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.chart-container {
    position: relative;
    width: 100%;
    height: 300px;
    margin-bottom: 10px;
}

.chart-status {
    text-align: center;
    color: var(--text-color-secondary);
    font-style: italic;
    font-size: 0.9rem;
}

.sessions-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.sessions-table th,
.sessions-table td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

.sessions-table th {
    background: var(--hover-bg);
    font-weight: bold;
    color: var(--text-color);
}

.clickable-name {
    color: #667eea;
    cursor: pointer;
    text-decoration: none;
    transition: color 0.2s ease;
}

.clickable-name:hover {
    color: #5a67d8;
    text-decoration: underline;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideIn {
    from { 
        opacity: 0;
        transform: translateY(-50px) scale(0.95);
    }
    to { 
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

/* Mobile responsive for modal */
@media (max-width: 768px) {
    .modal-content {
        max-width: 95vw;
        max-height: 95vh;
        margin: 10px;
    }
    
    .modal-header {
        padding: 15px 20px;
    }
    
    .modal-body {
        padding: 20px;
        max-height: calc(95vh - 80px);
    }
    
    .player-overview {
        grid-template-columns: 1fr;
        gap: 15px;
    }
    
    .metric-grid {
        grid-template-columns: 1fr;
    }
    
    .profession-tabs {
        gap: 5px;
    }
    
    .profession-tab {
        padding: 6px 12px;
        font-size: 0.9rem;
    }
}

/* Profession Filter Buttons */
.profession-filter {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
}

.profession-filter-btn {
    background: var(--button-bg);
    border: 1px solid var(--button-border);
    padding: 6px 12px;
    border-radius: 15px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: var(--text-color);
    font-size: 0.85rem;
}

.profession-filter-btn:hover {
    background: var(--button-hover);
}

.profession-filter-btn.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

@media (max-width: 768px) {
    .profession-filter {
        gap: 4px;
    }
    
    .profession-filter-btn {
        padding: 4px 8px;
        font-size: 0.8rem;
    }
}"""