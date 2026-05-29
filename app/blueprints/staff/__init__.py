from flask import Blueprint, session, render_template, redirect, url_for, flash
from app.db import get_db_connection



#建立藍圖
staff_bp = Blueprint('staff', __name__, template_folder = '../templates/staff') #建立藍圖


#註冊功能
from .product import product_bp
from .category import category_bp
from .page import page_bp

staff_bp.register_blueprint(product_bp, url_prefix='/product')
staff_bp.register_blueprint(category_bp, url_prefix='/category')
staff_bp.register_blueprint(page_bp, url_prefix='/page')



@staff_bp.route('/dashboard')
def dashboard():
    # 1. 如果沒有登入狀態就重導向至登入畫面
    if 'staff_id' not in session:
        return redirect(url_for('auth.staff_login'))
    
    # 2. 讀取 staff 資料
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM staff WHERE id = %s", (session['staff_id'],))
    user = cursor.fetchone()
    
    # 👇👇 3. 防護罩必須放在這裡！(拿到 user 後立刻檢查) 👇👇
    if not user:
        cursor.close()
        conn.close()
        session.clear()
        flash("找不到管理員資料，請重新登入")
        return redirect(url_for("auth.staff_login"))
    # 👆👆 ------------------------------------------------ 👆👆
    
    # 4. 確定 user 存在後，才安全地去撈他的 role (權限)
    cursor.execute("SELECT * FROM role WHERE id = %s", (user['role_id'],))
    role = cursor.fetchone()
    
    # 5. 關閉資料庫連線
    cursor.close()
    conn.close()
        
    return render_template('staff/dashboard.html', user = user, role = role)

