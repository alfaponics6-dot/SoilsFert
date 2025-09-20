#!/usr/bin/env python3
"""
Database migration script to add pro_plan_expires_at column
"""
import sqlite3
import os

def migrate_database():
    """Add the pro_plan_expires_at column to existing database"""
    db_path = 'soilfert.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'pro_plan_expires_at' in columns:
            print("✅ Column 'pro_plan_expires_at' already exists")
        else:
            # Add the column
            cursor.execute('ALTER TABLE users ADD COLUMN pro_plan_expires_at TIMESTAMP NULL')
            print("✅ Added 'pro_plan_expires_at' column to users table")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Running database migration...")
    if migrate_database():
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!")
