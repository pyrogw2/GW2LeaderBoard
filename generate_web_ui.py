#!/usr/bin/env python3
"""
Convenience script for web UI generation functionality.
This maintains backward compatibility while using the new package structure.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == '__main__':
    from gw2_leaderboard.web.generate_web_ui import main
    main()