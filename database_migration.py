#!/usr/bin/env python3
"""
Database Migration Script - PUCS
Voegt location en comment velden toe aan CallsignEntry table
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Migreer de database om location en comment velden toe te voegen"""
    
    db_path = 'radio_entry.db'
    
    if not os.path.exists(db_path):
        print("❌ Database bestand niet gevonden. Start eerst de applicatie om de database aan te maken.")
        return False
    
    # Maak backup van de database
    backup_path = f'radio_entry_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    
    try:
        # Kopieer database voor backup
        with open(db_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        print(f"✅ Database backup gemaakt: {backup_path}")
        
        # Verbind met database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check of kolommen al bestaan
        cursor.execute("PRAGMA table_info(callsign_entry)")
        columns = [column[1] for column in cursor.fetchall()]
        
        changes_made = False
        
        # Voeg location kolom toe als deze niet bestaat
        if 'location' not in columns:
            cursor.execute('ALTER TABLE callsign_entry ADD COLUMN location VARCHAR(100)')
            print("✅ Location kolom toegevoegd")
            changes_made = True
        else:
            print("ℹ️  Location kolom bestaat al")
        
        # Voeg comment kolom toe als deze niet bestaat  
        if 'comment' not in columns:
            cursor.execute('ALTER TABLE callsign_entry ADD COLUMN comment TEXT')
            print("✅ Comment kolom toegevoegd")
            changes_made = True
        else:
            print("ℹ️  Comment kolom bestaat al")
        
        if changes_made:
            conn.commit()
            print("✅ Database migratie succesvol voltooid!")
        else:
            print("ℹ️  Geen migratie nodig - database is al up-to-date")
        
        # Toon huidige tabel structuur
        cursor.execute("PRAGMA table_info(callsign_entry)")
        columns = cursor.fetchall()
        print("\n📋 Huidige tabel structuur:")
        for column in columns:
            print(f"   - {column[1]} ({column[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Fout tijdens migratie: {e}")
        return False

if __name__ == '__main__':
    print("🚀 PUCS Database Migratie Tool")
    print("=" * 40)
    
    success = migrate_database()
    
    if success:
        print("\n✅ Migratie voltooid! Je kunt nu de bijgewerkte applicatie starten.")
    else:
        print("\n❌ Migratie gefaald. Controleer de logs en probeer opnieuw.")