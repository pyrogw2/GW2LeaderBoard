#!/usr/bin/env python3
"""
Test script to compare sequential vs parallel database generation timing.
"""

import time
import os
import sys
from concurrent.futures import ThreadPoolExecutor

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from src.gw2_leaderboard.core.glicko_rating_system import calculate_date_filtered_ratings
except ImportError:
    try:
        sys.path.append('src')
        from gw2_leaderboard.core.glicko_rating_system import calculate_date_filtered_ratings
    except ImportError:
        print("Could not import calculate_date_filtered_ratings")
        print("Make sure you're running from the GW2LeaderBoard directory")
        sys.exit(1)

def test_sequential_generation(db_path, date_filters):
    """Test sequential DB generation."""
    print("=== SEQUENTIAL DB GENERATION ===")
    start_time = time.time()
    temp_dbs = []
    
    for date_filter in date_filters:
        db_start = time.time()
        print(f"  Generating {date_filter}...")
        try:
            temp_db_path = calculate_date_filtered_ratings(db_path, date_filter, guild_filter=False)
            temp_dbs.append(temp_db_path)
            db_time = time.time() - db_start
            print(f"  ✅ {date_filter}: {db_time:.1f}s")
        except Exception as e:
            print(f"  ❌ {date_filter}: {e}")
    
    total_time = time.time() - start_time
    print(f"Sequential total: {total_time:.1f}s")
    
    # Cleanup
    for temp_db in temp_dbs:
        try:
            os.remove(temp_db)
        except OSError:
            pass
    
    return total_time

def test_parallel_generation(db_path, date_filters):
    """Test parallel DB generation."""
    print("=== PARALLEL DB GENERATION ===")
    start_time = time.time()
    temp_dbs = []
    
    def generate_filtered_db(date_filter):
        db_start = time.time()
        print(f"  Generating {date_filter}...")
        try:
            temp_db_path = calculate_date_filtered_ratings(db_path, date_filter, guild_filter=False)
            db_time = time.time() - db_start
            print(f"  ✅ {date_filter}: {db_time:.1f}s")
            return temp_db_path
        except Exception as e:
            print(f"  ❌ {date_filter}: {e}")
            return None
    
    # Use ThreadPoolExecutor for parallel generation
    with ThreadPoolExecutor(max_workers=len(date_filters)) as executor:
        results = list(executor.map(generate_filtered_db, date_filters))
        temp_dbs = [db for db in results if db is not None]
    
    total_time = time.time() - start_time
    print(f"Parallel total: {total_time:.1f}s")
    
    # Cleanup
    for temp_db in temp_dbs:
        try:
            os.remove(temp_db)
        except OSError:
            pass
    
    return total_time

if __name__ == "__main__":
    db_path = "gw2_comprehensive.db"
    date_filters = ["30d", "60d", "90d"]
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found!")
        sys.exit(1)
    
    print(f"Testing DB generation for filters: {date_filters}")
    print(f"Source database: {db_path}")
    print()
    
    # Test sequential
    sequential_time = test_sequential_generation(db_path, date_filters)
    print()
    
    # Test parallel  
    parallel_time = test_parallel_generation(db_path, date_filters)
    print()
    
    # Compare results
    speedup = sequential_time / parallel_time if parallel_time > 0 else 0
    print("=== COMPARISON ===")
    print(f"Sequential: {sequential_time:.1f}s")
    print(f"Parallel:   {parallel_time:.1f}s")
    print(f"Speedup:    {speedup:.2f}x")
    
    if speedup > 1.1:
        print("✅ Parallel is significantly faster!")
    elif speedup < 0.9:
        print("❌ Parallel is slower (contention detected)")
    else:
        print("≈ Similar performance")