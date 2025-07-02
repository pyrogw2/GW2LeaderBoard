#!/usr/bin/env python3
"""
Setup script for GW2 WvW Leaderboard System
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gw2-leaderboard",
    version="1.0.0",
    author="GW2 Community",
    description="A comprehensive system for analyzing Guild Wars 2 WvW combat logs and generating skill-based rankings",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
        "beautifulsoup4>=4.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
        ],
    },
    entry_points={
        "console_scripts": [
            "gw2-sync=gw2_leaderboard.utils.sync_logs:main",
            "gw2-parse=gw2_leaderboard.parsers.parse_logs_enhanced:main",
            "gw2-rating=gw2_leaderboard.core.glicko_rating_system:main",
            "gw2-web=gw2_leaderboard.web.generate_web_ui:main",
            "gw2-guild=gw2_leaderboard.core.guild_manager:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="guild-wars-2 gw2 wvw leaderboard gaming statistics",
    project_urls={
        "Documentation": "https://github.com/username/gw2-leaderboard/tree/main/docs",
        "Source": "https://github.com/username/gw2-leaderboard",
        "Tracker": "https://github.com/username/gw2-leaderboard/issues",
    },
)