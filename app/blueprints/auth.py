from flask import Blueprint, render_template, request, redirect, url_for, session
from app.db import get_db_connection
from app.extensions import bcrypt
from datetime import datetime



auth_bp = Blueprint('auth', __name__, template_folder = '../templates/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        name = request.form['name']
        
        # 檢查密碼是否一致
        if password != confirm_password:
            return "<script>alert('兩次輸入的密碼不一致，請重新確認！'); window.history.back();</script>"
        
        phone = request.form.get('phone')
        region = request.form.get('region')
        locality = request.form.get('locality')
        address = request.form.get('address')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 檢查 Email 是否存在
        cursor.execute("SELECT id FROM customer WHERE email = %s", (email,))
        if cursor.fetchone():
            return "<script>alert('此 Email 已經註冊過囉！'); window.history.back();</script>"
        
        # 密碼加密
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            sql = """INSERT INTO customer (email, password, name, phone, region, locality, address, created_at, updated_at) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (email, hashed_pw, name, phone, region, locality, address, now, now))
            conn.commit()
            return "<script>alert('申辦成功！請重新登入。'); window.location.href = '/auth/login';</script>"
        except Exception as e:
            return f"<script>alert('系統錯誤: {str(e)}');</script>"
        finally:
            cursor.close()
            conn.close()
            
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'customer_id' in session:
        return redirect(url_for('customer.center'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customer WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user :
            if bcrypt.check_password_hash(user['password'], password):
                session['customer_id'] = user['id']
                return redirect(url_for('customer.center'))
            else:
                return "<script>alert('密碼錯囉，再試一次？'); window.history.back();</script>"
        else:
            return "<script>alert('電子郵件不存在'); window.history.back();</script>"
            
    return render_template('login.html')




@auth_bp.route('/logout', methods=['GET','POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

#管理員登入
@auth_bp.route('/staff_login', methods=['GET', 'POST'])
def staff_login():
    if 'staff_id' in session:
        return redirect(url_for('staff.dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM staff WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['staff_id'] = user['id']
            return redirect(url_for('staff.dashboard'))
        else:
            return "<script>alert('密碼錯囉，再試一次？'); window.history.back();</script>"
            
    return render_template('staff_login.html')

#管理員登出
@auth_bp.route('/staff_logout', methods=['GET','POST'])
def staff_logout():
    session.clear()
    return redirect(url_for('auth.staff_login'))