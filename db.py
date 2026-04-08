import psycopg2
import os

def get_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def get_data(table_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f'SELECT * FROM {table_name}')
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]
