from flask import Blueprint, session, render_template, redirect, url_for, flash
from app.db import get_db_connection
from app.extensions import bcrypt
from datetime import datetime



dashboard_bp = Blueprint('dashboard', __name__, template_folder = '../templates/admin') #建立藍圖


#儀錶板
@dashboard_bp.route('/dashboard')
def dashboard():
    #如果沒有登入狀態就重導向至登入畫面
    if 'admin_id' not in session:
        return redirect(url_for('auth.admin-login'))
    
    #讀取admin資料
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM admin WHERE id = %s", (session['admin_id'],))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM role WHERE id = %s", (user['role_id'],))
    role = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    #找不到資料時清空登入狀態病蟲
    if not user:
        session.clear()
        flash("找不到管理員資料")
        return redirect(url_for("auth.admin-login"))
        
    return render_template('admin/dashboard.html', user = user, role = role)