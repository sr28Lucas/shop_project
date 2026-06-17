from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from app.db import get_db_connection
from app.extensions import bcrypt
from datetime import datetime
from app.utils.validators import Validator
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import os

auth_bp = Blueprint('auth', __name__, template_folder='../templates/auth')

# 初始化 Mail 與 Serializer (Serializer 的金鑰建議從 current_app.config 取得比較安全)
mail = Mail()
# 預設金鑰，實務上會從 app config 拿
serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY', 'dev-key')) 

# --- 發送驗證信的輔助函式 ---
def send_verification_email(email, token):
    verify_url = url_for('auth.verify_email', token=token, _external=True)
    msg = Message(
        subject='[VIVID] 會員信箱驗證',
        recipients=[email],
        html=f'''
        <h2>歡迎加入我們的電商網站！</h2>
        <p>請點擊以下連結來啟用您的帳號：</p>
        <a href="{verify_url}" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">驗證信箱並啟用帳號</a>
        <p>此連結將在 1 小時後失效。</p>
        '''
    )
    mail.send(msg)


# --- 註冊功能 ---
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
        address = request.form.get('address', '').strip() or None
        
        if address and len(address) < 5:
            flash("詳細地址若輸入則至少需 5 個字元。", "error")
            return redirect(url_for('auth.register'))
        
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
            
            # 【關鍵修復 1】檢查 Email 是否存在與驗證狀態
            cursor.execute("SELECT id, is_verified, is_active FROM customer WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                if existing_user['is_verified'] == 1:
                    flash("此 Email 已經註冊過囉！", "error")
                    return redirect(url_for('auth.register'))
                else:
                    # 帳號存在但未驗證，刪除舊紀錄讓使用者重新註冊
                    cursor.execute("DELETE FROM customer WHERE email = %s", (email,))
                    conn.commit() 
            
            # 密碼加密
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 【關鍵修復 2】判斷是否為自動化測試腳本 (開後門)
            is_test_account = email.lower().endswith('@test.com')
            is_verified = 1 if is_test_account else 0
            is_active = 1 # 註冊時預設皆為 active (非停權)
            
            # 寫入資料庫
            sql = """INSERT INTO customer (email, password, name, phone, region_id, locality_id, address, is_active, is_verified, created_at, updated_at) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (email, hashed_pw, name, phone, region_id, locality_id, address, is_active, is_verified, now, now))
            
            # 【關鍵修復 3】發送驗證信 (測試帳號直接跳過不寄信)
            if not is_test_account:
                try:
                    token = serializer.dumps(email, salt='email-verify')
                    send_verification_email(email, token)
                except Exception as mail_err:
                    conn.rollback() # 把剛才 INSERT 的資料倒轉回去
                    flash("驗證信發送失敗，伺服器可能無回應，請稍後再試。", "error")
                    return redirect(url_for('auth.register'))
            
            conn.commit() # 正式寫入資料庫
            
            # 根據是否為測試帳號，給予不同的提示訊息
            if is_test_account:
                flash("測試帳號註冊成功！(已自動啟用，免驗證)", "success")
            else:
                flash("申辦成功！驗證信已發送至您的信箱，請點擊連結啟用帳號。", "success")
                
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


# --- 處理信箱驗證的路由 ---
@auth_bp.route('/verify/<token>')
def verify_email(token):
    try:
        # 嘗試解碼 token，設定 3600 秒 (1小時) 內有效
        email = serializer.loads(token, salt='email-verify', max_age=3600)
    except:
        flash("驗證連結無效或已過期，請重新註冊或聯絡客服。", "error")
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, is_verified FROM customer WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
             flash("找不到此帳號，請重新註冊。", "error")
             return redirect(url_for('auth.register'))
             
        if user['is_verified'] == 1:
             flash("帳號已經驗證過囉！請直接登入。", "success")
             return redirect(url_for('auth.login'))

        # 將使用者的 is_verified 狀態改為 1 (驗證通過)
        cursor.execute("UPDATE customer SET is_verified=1, updated_at=NOW() WHERE email=%s", (email,))
        conn.commit()

        flash("郵箱驗證成功！您的帳號已啟用，請登入。", "success")
    except Exception as e:
        if conn: conn.rollback()
        flash("驗證過程中發生錯誤，請稍後再試。", "error")
    finally:
        if conn:
            cursor.close()
            conn.close()

    return redirect(url_for('auth.login'))


# --- 會員登入 ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'customer_id' in session:
        return redirect(url_for('customer.center'))

    email = ''
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
            # 1. 檢查是否已驗證信箱
            if not user['is_verified']:
                flash("您的帳號尚未完成信箱驗證，請至信箱點擊驗證連結。", "error")
                return render_template('login.html', email=email)
            
            # 2. 檢查帳號是否被停權 (is_active)
            if not user['is_active']:
                flash("您的帳號已被停用，請聯絡客服人員。", "error")
                return render_template('login.html', email=email)
                
            if bcrypt.check_password_hash(user['password'], password):
                session['customer_id'] = user['id']
                return redirect(url_for('customer.center'))
            else:
                flash("密碼錯囉，再試一次？", "error")
                return render_template('login.html', email=email)
        else:
            flash("電子郵件不存在", "error")
            return render_template('login.html', email=email)
            
    return render_template('login.html')


# --- 會員登出 ---
@auth_bp.route('/logout', methods=['GET','POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# --- 忘記密碼 ---
@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM customer WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            token = serializer.dumps(email, salt='password-reset')
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            msg = Message(
                subject='[VIVID] 密碼重設通知',
                recipients=[email],
                html=f'''
                <h2>您申請了重設密碼</h2>
                <p>請點擊以下連結來設定您的新密碼：</p>
                <a href="{reset_url}" style="padding: 10px 20px; background-color: #d63384; color: white; text-decoration: none; border-radius: 5px;">重設密碼</a>
                <p>此連結將在 1 小時後失效。</p>
                '''
            )
            mail.send(msg)
            flash("重設密碼信已發送至您的信箱。", "success")
        else:
            # 安全性考量：即使 Email 不存在，也顯示發送成功的訊息
            flash("若此 Email 有註冊，重設連結已發送。", "success")
        
        cursor.close()
        conn.close()
        return redirect(url_for('auth.login'))
        
    return render_template('forgot_password.html')

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except:
        flash("重設連結無效或已過期。", "error")
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash("兩次密碼輸入不一致。", "error")
            return redirect(url_for('auth.reset_password', token=token))
            
        if not Validator.is_valid_password(new_password):
            flash("密碼長度至少需 4 位。", "error")
            return redirect(url_for('auth.reset_password', token=token))

        conn = get_db_connection()
        cursor = conn.cursor()
        hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
        cursor.execute("UPDATE customer SET password = %s, updated_at = NOW() WHERE email = %s", (hashed_pw, email))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash("密碼已重設，請使用新密碼登入。", "success")
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html')

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
            
    response = render_template('staff_login.html')
    # 使用 CSP 允許自身域名嵌套，解決後台 iframe 內容無法顯示的問題
    if isinstance(response, str):
        from flask import make_response
        response = make_response(response)
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
    return response

# --- 管理員登出 ---
@auth_bp.route('/staff_logout', methods=['GET','POST'])
def staff_logout():
    session.clear()
    return redirect(url_for('auth.staff_login'))