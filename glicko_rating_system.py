#!/usr/bin/env python3
"""
Convenience script for Glicko rating system functionality.
This maintains backward compatibility while using the new package structure.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == '__main__':
    from gw2_leaderboard.core.glicko_rating_system import main
    main()