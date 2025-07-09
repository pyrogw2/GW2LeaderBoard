#!/usr/bin/env python3
"""
Database migration script to remove composite_score column from glicko_ratings table.
This migrates the system to use pure Glicko ratings instead of composite scores.
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str) -> bool:
    """Remove composite_score column from glicko_ratings table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"🔄 Migrating database: {db_path}")
        
        # Check if composite_score column exists
        cursor.execute("PRAGMA table_info(glicko_ratings)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'composite_score' not in columns:
            print("✅ composite_score column not found - migration already complete")
            conn.close()
            return True
        
        print("📊 Current schema has composite_score column")
        
        # Create new table without composite_score
        print("🔨 Creating new table structure...")
        cursor.execute('''
            CREATE TABLE glicko_ratings_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                profession TEXT NOT NULL,
                metric_category TEXT NOT NULL,
                rating REAL DEFAULT 1500.0,
                rd REAL DEFAULT 350.0,
                volatility REAL DEFAULT 0.06,
                games_played INTEGER DEFAULT 0,
                total_rank_sum REAL DEFAULT 0.0,
                average_rank REAL DEFAULT 0.0,
                total_stat_value REAL DEFAULT 0.0,
                average_stat_value REAL DEFAULT 0.0,
                UNIQUE(account_name, profession, metric_category)
            )
        ''')
        
        # Copy data from old table (excluding composite_score)
        print("📦 Copying data to new table...")
        cursor.execute('''
            INSERT INTO glicko_ratings_new (
                account_name, profession, metric_category, rating, rd, volatility,
                games_played, total_rank_sum, average_rank, total_stat_value, average_stat_value
            )
            SELECT 
                account_name, profession, metric_category, rating, rd, volatility,
                games_played, total_rank_sum, average_rank, total_stat_value, average_stat_value
            FROM glicko_ratings
        ''')
        
        # Get row counts for verification
        cursor.execute("SELECT COUNT(*) FROM glicko_ratings")
        old_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM glicko_ratings_new")
        new_count = cursor.fetchone()[0]
        
        if old_count != new_count:
            print(f"❌ Row count mismatch: {old_count} -> {new_count}")
            conn.rollback()
            conn.close()
            return False
        
        print(f"✅ Copied {new_count} rows successfully")
        
        # Drop old table and rename new one
        print("🔄 Replacing old table...")
        cursor.execute("DROP TABLE glicko_ratings")
        cursor.execute("ALTER TABLE glicko_ratings_new RENAME TO glicko_ratings")
        
        # Recreate indexes
        print("📑 Recreating indexes...")
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_glicko_account_profession 
            ON glicko_ratings(account_name, profession)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_glicko_profession_metric 
            ON glicko_ratings(profession, metric_category)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_glicko_rating 
            ON glicko_ratings(rating DESC)
        ''')
        
        # Commit changes
        conn.commit()
        
        # Verify final schema
        cursor.execute("PRAGMA table_info(glicko_ratings)")
        final_columns = [row[1] for row in cursor.fetchall()]
        
        if 'composite_score' in final_columns:
            print("❌ Migration failed - composite_score still exists")
            conn.close()
            return False
        
        print("✅ Database migration completed successfully")
        print(f"📋 Final schema: {', '.join(final_columns)}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    """Main migration function."""
    db_path = "gw2_comprehensive.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return 1
    
    # Create backup
    backup_path = f"{db_path}.backup_before_composite_removal"
    print(f"📋 Creating backup: {backup_path}")
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print("✅ Backup created successfully")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return 1
    
    # Run migration
    if migrate_database(db_path):
        print("🎉 Migration completed successfully!")
        print(f"💾 Backup available at: {backup_path}")
        return 0
    else:
        print("❌ Migration failed!")
        print(f"🔄 Restore from backup: mv {backup_path} {db_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main())