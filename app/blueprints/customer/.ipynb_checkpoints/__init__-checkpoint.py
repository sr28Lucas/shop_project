from flask import Blueprint, session, render_template, redirect, url_for, flash
from app.db import get_db_connection
from app.extensions import bcrypt
from datetime import datetime



customer_bp = Blueprint('customer', __name__, template_folder = '../templates/customer') #建立藍圖


#會員中心
@customer_bp.route('/center')
def center():
    #如果沒有登入狀態就重導向至登入畫面
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    #讀取admin資料
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customer WHERE id = %s", (session['customer_id'],))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    #找不到資料時清空登入狀態並重新導向
    if not user:
        session.clear()
        flash("找不到會員資料")
        return redirect(url_for("auth.login"))
        
    return render_template('customer/center.html', user = user)