from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.db import get_db_connection
from app.extensions import bcrypt
from datetime import datetime
from app.utils.validators import Validator



auth_bp = Blueprint('auth', __name__, template_folder = '../templates/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name', '').strip()
        
        # 1. 統一驗證
        if not email or not password or not name:
            flash("請填寫所有必填欄位。", "error")
            return redirect(url_for('auth.register'))
            
        if not Validator.is_valid_email(email):
            flash("電子郵件格式不正確或長度超出範圍 (3-100)。", "error")
            return redirect(url_for('auth.register'))

        if not Validator.is_valid_name(name):
            flash("姓名長度需在 1-100 字元之間。", "error")
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash("兩次輸入的密碼不一致，請重新確認！", "error")
            return redirect(url_for('auth.register'))
        
        if not Validator.is_valid_password(password):
            flash("密碼長度至少需 4 位。", "error")
            return redirect(url_for('auth.register'))

        phone = request.form.get('phone', '').strip() or None
        if phone and not Validator.is_valid_phone(phone):
            flash("電話長度需在 8-30 碼之間。", "error")
            return redirect(url_for('auth.register'))
        region_name = request.form.get('region') or None
        locality_name = request.form.get('locality') or None
        address = request.form.get('address') or None
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 獲取 Region ID
            region_id = None
            if region_name:
                cursor.execute("SELECT id FROM region WHERE name = %s", (region_name,))
                res = cursor.fetchone()
                if res:
                    region_id = res['id']
                    
            # 獲取 Locality ID
            locality_id = None
            if locality_name and region_id:
                cursor.execute("SELECT id FROM locality WHERE name = %s AND region_id = %s", (locality_name, region_id))
                res = cursor.fetchone()
                if res:
                    locality_id = res['id']
            
            # 檢查 Email 是否存在
            cursor.execute("SELECT id FROM customer WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("此 Email 已經註冊過囉！", "error")
                return redirect(url_for('auth.register'))
            
            # 密碼加密
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            sql = """INSERT INTO customer (email, password, name, phone, region_id, locality_id, address, created_at, updated_at) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (email, hashed_pw, name, phone, region_id, locality_id, address, now, now))
            conn.commit()
            
            flash("申辦成功！請重新登入。", "success")
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            if conn: conn.rollback()
            flash(f"系統錯誤: {str(e)}", "error")
            return redirect(url_for('auth.register'))
        finally:
            if conn:
                cursor.close()
                conn.close()
            
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'customer_id' in session:
        return redirect(url_for('customer.center'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customer WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            if not user['is_active']:
                flash("您的帳號已被停用，請聯絡管理員。", "error")
                return redirect(url_for('auth.login'))
            if bcrypt.check_password_hash(user['password'], password):
                session['customer_id'] = user['id']
                return redirect(url_for('customer.center'))
            else:
                flash("密碼錯囉，再試一次？", "error")
                return redirect(url_for('auth.login'))
        else:
            flash("電子郵件不存在", "error")
            return redirect(url_for('auth.login'))
            
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
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM staff WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            if not user['is_active']:
                flash("您的員工帳號已被停用，請聯絡系統管理員。", "error")
                return redirect(url_for('auth.staff_login'))
            if bcrypt.check_password_hash(user['password'], password):
                session['staff_id'] = user['id']
                return redirect(url_for('staff.dashboard'))
            else:
                flash("密碼錯囉，再試一次？", "error")
                return redirect(url_for('auth.staff_login'))
        else:
            flash("帳號不存在", "error")
            return redirect(url_for('auth.staff_login'))
            
    return render_template('staff_login.html')

#管理員登出
@auth_bp.route('/staff_logout', methods=['GET','POST'])
def staff_logout():
    session.clear()
    return redirect(url_for('auth.staff_login'))