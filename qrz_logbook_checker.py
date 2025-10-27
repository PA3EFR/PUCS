#!/usr/bin/env python3
"""
QRZ Logbook Checker Service
Controleert elke minuut het QRZ logboek en verwijdert gelogde callsigns uit de entry list
"""

import os
import time
import requests
import html
import urllib.parse
import sqlite3
from datetime import datetime, timedelta
import threading
import re
from contextlib import contextmanager

class QRZLogbookChecker:
    def __init__(self, db_path='instance/radio_entry.db'):
        self.db_path = db_path
        self.running = False
        self.check_thread = None
        self.interval = 60  # 1 minuut in seconden
        
    def log(self, message):
        """Log met timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] QRZ Checker: {message}")
        
    @contextmanager
    def get_db_connection(self):
        """Database connectie context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
            
    def get_qrz_config(self):
        """Haal QRZ configuratie op uit database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT callsign, api_key FROM qrz_config ORDER BY updated_at DESC LIMIT 1")
                row = cursor.fetchone()
                
                if row:
                    return row['callsign'], row['api_key']
                else:
                    # Fallback naar default waarden
                    self.log("Geen QRZ configuratie gevonden, gebruik default waarden")
                    return 'PH25XMAS', '4DB9-.....-579F'
                    
        except Exception as e:
            self.log(f"Fout bij ophalen QRZ config: {e}")
            return 'PH25XMAS', '4DB9-.....-579F'
            
    def get_active_callsigns(self):
        """Haal actieve callsigns op uit database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT callsign FROM callsign_entry")
                rows = cursor.fetchall()
                return [row['callsign'] for row in rows]
                
        except Exception as e:
            self.log(f"Fout bij ophalen actieve callsigns: {e}")
            return []
            
    def remove_callsign_from_db(self, callsign):
        """Verwijder callsign uit database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM callsign_entry WHERE callsign = ?", (callsign,))
                if cursor.rowcount > 0:
                    conn.commit()
                    self.log(f"✅ Callsign {callsign} verwijderd uit entry list")
                    return True
                return False
                
        except Exception as e:
            self.log(f"Fout bij verwijderen callsign {callsign}: {e}")
            return False
            
    def fetch_qrz_logbook(self, callsign, api_key):
        """Haal QRZ logboek op via API"""
        try:
            params = {
                "KEY": api_key,
                "ACTION": "FETCH",
                "ADIF": 1
            }
            
            response = requests.get("https://logbook.qrz.com/api", params=params, timeout=30)
            if response.status_code != 200:
                self.log(f"❌ QRZ API fout: HTTP {response.status_code}")
                return None
                
            decoded = html.unescape(response.text)
            parsed = urllib.parse.parse_qs(decoded)
            adif_data = parsed.get("ADIF", [""])[0]
            
            if not adif_data:
                self.log("⚠️ Geen ADIF data ontvangen van QRZ")
                return None
                
            return adif_data
            
        except requests.exceptions.Timeout:
            self.log("❌ QRZ API timeout")
            return None
        except Exception as e:
            self.log(f"❌ Fout bij ophalen QRZ logboek: {e}")
            return None
            
    def parse_callsigns_from_adif(self, adif_data):
        """Parseer callsigns uit ADIF data"""
        try:
            # Simpele regex om callsigns te vinden in ADIF formaat
            # Zoekt naar <CALL:lengte>callsign patronen
            callsign_pattern = r'<CALL:\d+>([A-Z0-9/]+)'
            matches = re.findall(callsign_pattern, adif_data, re.IGNORECASE)
            
            # Maak unieke lijst en converteer naar uppercase
            unique_callsigns = list(set([call.upper() for call in matches]))
            
            self.log(f"📋 {len(unique_callsigns)} unieke callsigns gevonden in logboek")
            return unique_callsigns
            
        except Exception as e:
            self.log(f"❌ Fout bij parsen ADIF data: {e}")
            return []
            
    def get_latest_callsign_from_adif(self, adif_data):
        """Haal de laatste (meest recente) callsign uit ADIF data"""
        try:
            # Split ADIF data in individuele QSO records
            # ADIF records worden gescheiden door <EOR> (End of Record)
            qso_records = adif_data.split('<EOR>')
            
            latest_callsign = None
            latest_timestamp = None
            
            for record in qso_records:
                record = record.strip()
                if not record:
                    continue
                    
                # Parse callsign uit record
                call_match = re.search(r'<CALL:(\d+)>([A-Z0-9/]+)', record, re.IGNORECASE)
                if not call_match:
                    continue
                    
                callsign = call_match.group(2).upper()
                
                # Parse timestamp uit record (QSO_DATE en TIME_ON)
                qso_date_match = re.search(r'<QSO_DATE:(\d+)>(\d{8})', record)
                time_match = re.search(r'<TIME_ON:(\d+)>(\d{4,6})', record)
                
                if qso_date_match and time_match:
                    # Combineer datum en tijd tot timestamp
                    date_str = qso_date_match.group(2)
                    time_str = time_match.group(2)
                    timestamp_str = date_str + time_str.zfill(6)  # Zorg dat tijd 6 cijfers heeft
                    
                    try:
                        # Vergelijk timestamps en hou de nieuwste bij
                        if latest_timestamp is None or timestamp_str > latest_timestamp:
                            latest_timestamp = timestamp_str
                            latest_callsign = callsign
                    except:
                        # Fallback als timestamp parsing faalt
                        latest_callsign = callsign
                else:
                    # Fallback: laatste gevonden callsign gebruiken
                    latest_callsign = callsign
            
            if latest_callsign:
                self.log(f"🎯 Laatste callsign gevonden: {latest_callsign}")
                return latest_callsign
            else:
                self.log("⚠️ Geen callsigns met timestamp gevonden in ADIF")
                return None
                
        except Exception as e:
            self.log(f"❌ Fout bij ophalen laatste callsign uit ADIF: {e}")
            return None
            
    def check_and_remove_logged_callsigns(self):
        """Hoofdfunctie: check logboek en verwijder gelogde callsigns"""
        try:
            # Haal QRZ configuratie op
            qrz_callsign, api_key = self.get_qrz_config()
            
            if not qrz_callsign or not api_key:
                self.log("⚠️ Geen geldige QRZ configuratie beschikbaar")
                return
                
            # Haal actieve callsigns op
            active_callsigns = self.get_active_callsigns()
            
            if not active_callsigns:
                self.log("📭 Geen actieve callsigns om te controleren")
                return
                
            self.log(f"🔍 Controleer {len(active_callsigns)} actieve callsigns tegen {qrz_callsign} logboek")
            
            # Haal QRZ logboek op
            adif_data = self.fetch_qrz_logbook(qrz_callsign, api_key)
            
            if not adif_data:
                self.log("❌ Kan QRZ logboek niet ophalen")
                return
                
            # Parseer callsigns uit logboek
            logged_callsigns = self.parse_callsigns_from_adif(adif_data)
            
            if not logged_callsigns:
                self.log("📭 Geen callsigns gevonden in logboek")
                return
                
            # Check welke actieve callsigns al gelogd zijn
            removed_count = 0
            for callsign in active_callsigns:
                if callsign in logged_callsigns:
                    if self.remove_callsign_from_db(callsign):
                        removed_count += 1
                        
            if removed_count > 0:
                self.log(f"🎯 {removed_count} callsign(s) verwijderd uit entry list")
            else:
                self.log("👍 Geen callsigns hoeven verwijderd te worden")
                
        except Exception as e:
            self.log(f"❌ Fout tijdens logboek check: {e}")
            
    def check_loop(self):
        """Hoofdloop die elke minuut draait"""
        self.log(f"🚀 QRZ Logbook Checker gestart (interval: {self.interval}s)")
        
        while self.running:
            try:
                self.check_and_remove_logged_callsigns()
                
                # Wacht interval seconden, maar check elke seconde of we moeten stoppen
                for i in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(5)
                    
            except KeyboardInterrupt:
                self.log("🛑 Onderbroken door gebruiker")
                break
            except Exception as e:
                self.log(f"❌ Onverwachte fout in hoofdloop: {e}")
                time.sleep(5)  # Korte pauze bij fouten
                
        self.log("🛑 QRZ Logbook Checker gestopt")
        
    def start(self):
        """Start de checker service"""
        if self.running:
            self.log("⚠️ Service draait al")
            return
            
        self.running = True
        self.check_thread = threading.Thread(target=self.check_loop, daemon=True)
        self.check_thread.start()
        self.log("✅ Service gestart als background thread")
        
    def stop(self):
        """Stop de checker service"""
        if not self.running:
            self.log("⚠️ Service draait niet")
            return
            
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        self.log("✅ Service gestopt")
        
    def is_running(self):
        """Check of service draait"""
        return self.running and self.check_thread and self.check_thread.is_alive()


class QRZLatestCallsignMonitor:
    """
    Monitor voor de laatste ingevoerde callsign in QRZ logboek.
    Checkt elke minuut de laatste callsign en verwijdert deze automatisch uit PUCS als gevonden.
    """
    def __init__(self, db_path='instance/radio_entry.db'):
        self.db_path = db_path
        self.running = False
        self.monitor_thread = None
        self.interval = 60  # 1 minuut in seconden
        self.last_checked_callsign = None  # Om herhaalde checks te voorkomen
        
    def log(self, message):
        """Log met timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] QRZ Latest Monitor: {message}")
        
    @contextmanager
    def get_db_connection(self):
        """Database connectie context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
            
    def get_qrz_config(self):
        """Haal QRZ configuratie op uit database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT callsign, api_key FROM qrz_config ORDER BY updated_at DESC LIMIT 1")
                row = cursor.fetchone()
                
                if row:
                    return row['callsign'], row['api_key']
                else:
                    # Fallback naar default waarden
                    self.log("Geen QRZ configuratie gevonden, gebruik default waarden")
                    return 'PH25XMAS', '4DB9-7013-A9B4-579F'
                    
        except Exception as e:
            self.log(f"Fout bij ophalen QRZ config: {e}")
            return 'PH25XMAS', '4DB9-....-579F'
            
    def check_callsign_in_pucs(self, callsign):
        """Check of callsign bestaat in PUCS entries"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM callsign_entry WHERE callsign = ?", (callsign,))
                row = cursor.fetchone()
                return row is not None
                
        except Exception as e:
            self.log(f"Fout bij checken callsign {callsign} in PUCS: {e}")
            return False
            
    def remove_callsign_from_pucs(self, callsign):
        """Verwijder callsign uit PUCS entries"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM callsign_entry WHERE callsign = ?", (callsign,))
                if cursor.rowcount > 0:
                    conn.commit()
                    self.log(f"🗑️ Callsign {callsign} automatisch verwijderd uit PUCS (was gelogd in QRZ)")
                    return True
                return False
                
        except Exception as e:
            self.log(f"Fout bij verwijderen callsign {callsign}: {e}")
            return False
            
    def monitor_latest_callsign(self):
        """
        Monitor functie: haal laatste callsign uit QRZ en check tegen PUCS
        """
        try:
            # Haal QRZ configuratie op
            qrz_callsign, api_key = self.get_qrz_config()
            
            if not qrz_callsign or not api_key:
                self.log("⚠️ Geen geldige QRZ configuratie beschikbaar")
                return False
                
            self.log(f"🔍 Monitor QRZ logboek van {qrz_callsign} voor laatste callsign...")
            
            # Haal QRZ logboek op
            qrz_checker_instance = QRZLogbookChecker(self.db_path)
            adif_data = qrz_checker_instance.fetch_qrz_logbook(qrz_callsign, api_key)
            
            if not adif_data:
                self.log("❌ Kan QRZ logboek niet ophalen")
                return False
                
            # Haal laatste callsign op
            latest_callsign = qrz_checker_instance.get_latest_callsign_from_adif(adif_data)
            
            if not latest_callsign:
                self.log("📭 Geen laatste callsign gevonden in QRZ logboek")
                return False
                
            # Skip als we deze callsign al gecheckt hebben
            if latest_callsign == self.last_checked_callsign:
                return True
                
            self.log(f"🎯 Laatste QRZ callsign: {latest_callsign}")
            
            # Check of callsign bestaat in PUCS
            if self.check_callsign_in_pucs(latest_callsign):
                self.log(f"✅ Callsign {latest_callsign} gevonden in PUCS, verwijderen...")
                if self.remove_callsign_from_pucs(latest_callsign):
                    self.last_checked_callsign = latest_callsign
                    return True
                else:
                    self.log(f"❌ Kon callsign {latest_callsign} niet verwijderen uit PUCS")
            else:
                self.log(f"ℹ️ Callsign {latest_callsign} niet gevonden in PUCS, wachten...")
                
            # Update last checked callsign
            self.last_checked_callsign = latest_callsign
            return True
            
        except Exception as e:
            self.log(f"❌ Fout tijdens monitoren laatste callsign: {e}")
            return False
            
    def monitor_loop(self):
        """Hoofdmonitor loop - draait continu"""
        self.log(f"🚀 QRZ Latest Callsign Monitor gestart (interval: {self.interval}s)")
        
        while self.running:
            try:
                # Voer monitor check uit
                self.monitor_latest_callsign()
                
                # Wacht interval seconden, maar check elke 5 seconden of we moeten stoppen
                for i in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(5)
                    
            except KeyboardInterrupt:
                self.log("🛑 Onderbroken door gebruiker")
                break
            except Exception as e:
                self.log(f"❌ Onverwachte fout in monitor loop: {e}")
                time.sleep(5)  # Korte pauze bij fouten
                
        self.log("🛑 QRZ Latest Callsign Monitor gestopt")
        
    def start(self):
        """Start de monitor service"""
        if self.running:
            self.log("⚠️ Monitor service draait al")
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.log("✅ Monitor service gestart als background thread")
        
    def stop(self):
        """Stop de monitor service"""
        if not self.running:
            self.log("⚠️ Monitor service draait niet")
            return
            
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.log("✅ Monitor service gestopt")
        
    def is_running(self):
        """Check of service draait"""
        return self.running and self.monitor_thread and self.monitor_thread.is_alive()


# Global instances
qrz_checker = QRZLogbookChecker()
qrz_latest_monitor = QRZLatestCallsignMonitor()

def start_qrz_service():
    """Start QRZ service (voor gebruik in Flask app)"""
    qrz_checker.start()
    
def stop_qrz_service():
    """Stop QRZ service (voor gebruik in Flask app)"""
    qrz_checker.stop()
    
def get_qrz_service_status():
    """Get service status"""
    return qrz_checker.is_running()

# =============================================================================
# LATEST CALLSIGN MONITOR FUNCTIONS
# =============================================================================

def start_latest_callsign_monitor():
    """Start QRZ latest callsign monitor service"""
    try:
        qrz_latest_monitor.start()
        print("✅ QRZ Latest Callsign Monitor gestart")
    except Exception as e:
        print(f"❌ Fout bij starten QRZ latest monitor: {e}")
        
def stop_latest_callsign_monitor():
    """Stop QRZ latest callsign monitor service"""
    try:
        qrz_latest_monitor.stop()
        print("✅ QRZ Latest Callsign Monitor gestopt")
    except Exception as e:
        print(f"❌ Fout bij stoppen QRZ latest monitor: {e}")
        
def get_latest_monitor_status():
    """Get latest monitor service status"""
    return qrz_latest_monitor.is_running()

def get_latest_monitor_info():
    """Get detailed info about latest monitor service"""
    return {
        'running': qrz_latest_monitor.running,
        'interval': qrz_latest_monitor.interval,
        'last_checked_callsign': qrz_latest_monitor.last_checked_callsign,
        'status': 'Actief' if qrz_latest_monitor.is_running() else 'Gestopt'
    }

if __name__ == '__main__':
    # Voor standalone gebruik - beide services starten
    import signal
    import sys
    
    def signal_handler(sig, frame):
        print('\n🛑 SIGINT ontvangen, stoppen...')
        qrz_checker.stop()
        qrz_latest_monitor.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print("🚀 Starten van beide QRZ services...")
        qrz_checker.start()
        qrz_latest_monitor.start()
        
        # Houd het hoofdprogramma draaiende
        while True:
            time.sleep(1)
            if not (qrz_checker.is_running() and qrz_latest_monitor.is_running()):
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Keyboard interrupt ontvangen")
    finally:
        print("🛑 Stoppen van beide services...")
        qrz_checker.stop()
        qrz_latest_monitor.stop()