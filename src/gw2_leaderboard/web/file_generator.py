"""
File generation orchestration for GW2 WvW Leaderboards web UI.
Coordinates all modules to generate the complete web interface.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add current directory to Python path to import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Handle both relative and absolute imports
try:
    from .templates.html_templates import get_main_html_template
    from .templates.css_styles import get_css_content
    from .templates.javascript_ui import get_javascript_content
    from .data_processing import generate_player_summaries
    from .parallel_processing import generate_all_leaderboard_data
except ImportError:
    # Fall back to absolute imports for standalone execution
    from templates.html_templates import get_main_html_template
    from templates.css_styles import get_css_content
    from templates.javascript_ui import get_javascript_content
    from data_processing import generate_player_summaries
    from parallel_processing import generate_all_leaderboard_data


def generate_web_ui_files(data: Dict[str, Any], output_dir: Path) -> None:
    """Generate all web UI files (HTML, CSS, JS) from data."""
    print("Generating web UI files...")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML file
    html_content = get_main_html_template()
    html_file = output_dir / "index.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"  Generated: {html_file}")
    
    # Generate CSS file
    css_content = get_css_content()
    css_file = output_dir / "styles.css"
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(css_content)
    print(f"  Generated: {css_file}")
    
    # Generate JavaScript file
    js_content = get_javascript_content(data)
    js_file = output_dir / "script.js"
    with open(js_file, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f"  Generated: {js_file}")
    
    print("✅ Web UI files generated successfully")


def generate_complete_web_ui(db_path: str, output_dir: Path, 
                           date_filters: List[str] = None,
                           guild_enabled: bool = False,
                           guild_name: str = "",
                           guild_tag: str = "") -> None:
    """Generate complete web UI with all data and files."""
    if date_filters is None:
        date_filters = ["30d", "60d", "90d", "overall"]
    
    print("🚀 Starting complete web UI generation...")
    
    # Step 1: Generate all leaderboard data
    data = generate_all_leaderboard_data(
        db_path=db_path,
        date_filters=date_filters,
        guild_enabled=guild_enabled,
        guild_name=guild_name,
        guild_tag=guild_tag
    )
    
    # Step 2: Generate player summaries
    player_summaries = generate_player_summaries(
        db_path=db_path,
        output_dir=output_dir,
        date_filters=date_filters
    )
    
    # Step 3: Generate web UI files
    generate_web_ui_files(data, output_dir)
    
    print("🎉 Complete web UI generation finished!")
    return data