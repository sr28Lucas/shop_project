from flask import Blueprint, render_template, request
from app.db import get_db_connection
from .permission import require_role

db_viewer_bp = Blueprint('db_viewer', __name__)

@db_viewer_bp.route('/list')
@require_role('root')
def db_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('staff/db_viewer.html', tables=tables, active_table=None)

@db_viewer_bp.route('/view/<table>')
@require_role('root')
def db_view(table):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Simple search
    search = request.args.get('search', '')
    
    # Get column names first to build search query safely
    cursor.execute(f"DESCRIBE `{table}`")
    columns = [row['Field'] for row in cursor.fetchall()]
    
    query = f"SELECT * FROM `{table}`"
    params = []
    
    if search:
        where_clauses = [f"`{col}` LIKE %s" for col in columns]
        query += " WHERE " + " OR ".join(where_clauses)
        params = [f"%{search}%" for _ in columns]
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('staff/db_viewer.html', tables=get_all_tables(), active_table=table, columns=columns, rows=rows, search=search)

def get_all_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return tables
