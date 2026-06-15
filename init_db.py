import mysql.connector
from app.config import config

def init_db():
    conn = mysql.connector.connect(**config.DB_CONFIG)
    cursor = conn.cursor()
    tables = ['category', 'product', 'variant', 'sku', 'promo_code', 'announcement']
    for table in tables:
        try:
            print(f"Updating {table}...")
            cursor.execute(f"UPDATE {table} SET is_deleted = 0 WHERE is_deleted IS NULL")
        except Exception as e:
            print(f"Error updating {table}: {e}")
    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialization complete.")

if __name__ == '__main__':
    init_db()
