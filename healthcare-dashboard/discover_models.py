# healthcare-dashboard/discover_models.py
from django_etl import DjangoETL, DJANGO_DB_PATH

def discover_django_models():
    etl = DjangoETL(db_path=DJANGO_DB_PATH)
    
    if not etl.connect():
        print("❌ Could not connect to database")
        return
    
    tables = etl.get_tables()
    print(f"📊 Found {len(tables)} tables:")
    print("="*60)
    
    for table in tables:
        print(f"\n📌 {table}")
        schema = etl.get_table_schema(table)
        print("   Columns:")
        for col in schema:
            print(f"     - {col['name']} ({col['type']})")
        
        # Get sample data
        cursor = etl.connection.cursor()
        cursor.execute(f"SELECT * FROM {table} LIMIT 3")
        rows = cursor.fetchall()
        if rows:
            print("   Sample data (first 5 columns):")
            for row in rows:
                row_dict = dict(row)
                sample = {k: row_dict[k] for k in list(row_dict.keys())[:5]}
                print(f"     {sample}")
    
    etl.connection.close()

if __name__ == "__main__":
    discover_django_models()