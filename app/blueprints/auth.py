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
        name = request.form['name']
        phone = request.form.get('phone')
        region = request.form.get('region')
        locality = request.form.get('locality')
        address = request.form.get('address')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 檢查 Email 是否存在
        cursor.execute("SELECT id FROM member WHERE email = %s", (email,))
        if cursor.fetchone():
            return "<script>alert('此 Email 已經註冊過囉！'); window.history.back();</script>"
        
        # 密碼加密
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            sql = """INSERT INTO member (email, password, name, phone, region, locality, address, created_at, updated_at) 
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
    if 'member_id' in session:
        return redirect(url_for('member.center'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM member WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user :
            if bcrypt.check_password_hash(user['password'], password):
                session['member_id'] = user['id']
                return redirect(url_for('member.center'))
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
@auth_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if 'admin_id' in session:
        return redirect(url_for('admin.dashboard.dashboard'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['admin_id'] = user['id']
            return redirect(url_for('admin.dashboard'))
        else:
            return "<script>alert('密碼錯囉，再試一次？'); window.history.back();</script>"
            
    return render_template('admin_login.html')

#管理員登出
@auth_bp.route('/admin_logout', methods=['GET','POST'])
def admin_logout():
    session.clear()
    return redirect(url_for('auth.admin_login'))