from flask import session, redirect, url_for, flash, g
from app.db import get_db_connection

def get_staff_role():
    if 'staff_role' not in g:
        staff_id = session.get('staff_id')
        if not staff_id:
            return None
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 取得員工角色 ID
        cursor.execute("SELECT role_id FROM staff WHERE id = %s", (staff_id,))
        staff = cursor.fetchone()
        
        if not staff:
            cursor.close()
            conn.close()
            return None
            
        # 取得角色權限
        cursor.execute("SELECT * FROM role WHERE id = %s", (staff['role_id'],))
        role = cursor.fetchone()
        
        if not role:
            cursor.close()
            conn.close()
            # 若找不到角色，則設為無權限的空 dict
            g.staff_role = {}
            return g.staff_role
            
        g.staff_role = role
        
        cursor.close()
        conn.close()
    return g.staff_role

def check_permission(permission_name):
    """
    檢查當前登入的 staff 是否具備特定權限
    permission_name: role 資料表中的欄位名稱 (如: 'member', 'orders', 'product'...)
    """
    role = get_staff_role()
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
