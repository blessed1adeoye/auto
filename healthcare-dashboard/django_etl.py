# healthcare-dashboard/django_etl.py
# django_etl.py
import pandas as pd
import sqlite3
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/django_etl.log'),
        logging.StreamHandler()
    ]
)

class DjangoETL:
    def __init__(self, db_path=None):
        # Path to your Django database on the other account
        # Note: This might not work if PythonAnywhere restricts cross-account access
        self.db_path = db_path or '/home/himuch/clinic_form/db.sqlite3'
        self.connection = None
        
    def connect(self):
        try:
            if not os.path.exists(self.db_path):
                logging.error(f"❌ Database not found: {self.db_path}")
                logging.info("ℹ️ Make sure the path is correct or use Option B below")
                return False
            
            self.connection = sqlite3.connect(self.db_path)
            logging.info(f"✅ Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to connect: {e}")
            return False
    
    def extract_data(self):
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            # Auto-discover tables
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Find clinic-related table
            clinic_tables = [t for t in tables if 'clinic' in t.lower() or 'patient' in t.lower()]
            table_name = clinic_tables[0] if clinic_tables else tables[0]
            
            logging.info(f"📊 Reading from table: {table_name}")
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.connection)
            
            if df.empty:
                logging.info("ℹ️ No data found")
                return pd.DataFrame()
            
            logging.info(f"✅ Extracted {len(df)} records")
            return df
            
        except Exception as e:
            logging.error(f"❌ Error extracting data: {e}")
            return None

# Configuration
DJANGO_DB_PATH = '/home/himuch/clinic_form/db.sqlite3'

def fetch_from_django():
    etl = DjangoETL(db_path=DJANGO_DB_PATH)
    return etl.extract_data()

if __name__ == "__main__":
    df = fetch_from_django()
    if df is not None and not df.empty:
        print(f"✅ Successfully loaded {len(df)} records")
        print(df.head())