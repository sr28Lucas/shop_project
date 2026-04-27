from flask import Blueprint, session, render_template, redirect, url_for, flash
from app.db import get_db_connection



#建立藍圖
admin_bp = Blueprint('admin', __name__, template_folder = '../templates/admin') #建立藍圖


#註冊功能
from .product import product_bp


admin_bp.register_blueprint(product_bp, url_prefix='/product')




@admin_bp.route('/dashboard')
def dashboard():
    #如果沒有登入狀態就重導向至登入畫面
    if 'admin_id' not in session:
        return redirect(url_for('auth.admin_login'))
    
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
        return redirect(url_for("auth.admin_login"))
        
    return render_template('admin/dashboard.html', user = user, role = role)

