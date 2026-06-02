from flask import session, redirect, url_for, flash
from app.db import get_db_connection

def check_permission(permission_name):
    """
    檢查當前登入的 staff 是否具備特定權限
    permission_name: role 資料表中的欄位名稱 (如: 'member', 'orders', 'product'...)
    """
    staff_id = session.get('staff_id')
    if not staff_id:
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 取得員工角色 ID
    cursor.execute("SELECT role_id FROM staff WHERE id = %s", (staff_id,))
    staff = cursor.fetchone()
    
    if not staff:
        cursor.close()
        conn.close()
        return False
        
    # 檢查角色權限
    cursor.execute(f"SELECT {permission_name} FROM role WHERE id = %s", (staff['role_id'],))
    role = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return role and role.get(permission_name) == 1

def require_permission(permission_name):
    """
    用於路由的裝飾器檢查，若無權限則導向 dashboard
    """
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_permission(permission_name):
                flash('您沒有權限執行此操作')
                return redirect(url_for('staff.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
