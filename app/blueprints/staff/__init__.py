from flask import Blueprint, session, render_template, redirect, url_for, flash
from app.db import get_db_connection



#建立藍圖
staff_bp = Blueprint('staff', __name__, template_folder = '../templates/staff') #建立藍圖


#註冊功能
from .product import product_bp


staff_bp.register_blueprint(product_bp, url_prefix='/product')




@staff_bp.route('/dashboard')
def dashboard():
    #如果沒有登入狀態就重導向至登入畫面
    if 'staff_id' not in session:
        return redirect(url_for('auth.staff_login'))
    
    #讀取staff資料
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM staff WHERE id = %s", (session['staff_id'],))
    user = cursor.fetchone()
    cursor.execute("SELECT * FROM role WHERE id = %s", (user['role_id'],))
    role = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    #找不到資料時清空登入狀態病蟲
    if not user:
        session.clear()
        flash("找不到管理員資料")
        return redirect(url_for("auth.staff_login"))
        
    return render_template('staff/dashboard.html', user = user, role = role)

