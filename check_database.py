#!/usr/bin/env python3
"""
Database Check Tool - PUCS
Controleert of de database correct is gemigreerd
"""

import sqlite3
import os

def check_database():
    """Check database structuur en inhoud"""
    
    db_path = 'radio_entry.db'
    
    if not os.path.exists(db_path):
        print("❌ Database bestand niet gevonden")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tabel structuur
        cursor.execute("PRAGMA table_info(callsign_entry)")
        columns = cursor.fetchall()
        
        print("📋 Database Tabel Structuur:")
        column_names = []
        for column in columns:
            print(f"   - {column[1]} ({column[2]})")
            column_names.append(column[1])
        
        # Check of nieuwe kolommen bestaan
        has_location = 'location' in column_names
        has_comment = 'comment' in column_names
        
        print(f"\n✅ Location kolom: {'JA' if has_location else 'NEE'}")
        print(f"✅ Comment kolom: {'JA' if has_comment else 'NEE'}")
        
        # Check huidige entries
        cursor.execute("SELECT * FROM callsign_entry")
        entries = cursor.fetchall()
        
        print(f"\n📊 Totaal entries: {len(entries)}")
        
        if entries:
            print("\n📝 Huidige Entries:")
            for entry in entries:
                if has_location and has_comment:
                    print(f"   Positie {entry[1]}: {entry[2]} | QTH: {entry[3] or 'Geen'} | Remarks: {entry[4] or 'Geen'}")
                else:
                    print(f"   Positie {entry[1]}: {entry[2]}")
        
        conn.close()
        return has_location and has_comment
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == '__main__':
    print("🔍 PUCS Database Check Tool")
    print("=" * 40)
    
    success = check_database()
    
    if success:
        print("\n✅ Database is correct gemigreerd!")
    else:
        print("\n❌ Database migratie nodig. Run: python3 database_migration.py")