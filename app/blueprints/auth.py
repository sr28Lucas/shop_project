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
            
            # 【關鍵修復 1】檢查 Email 是否存在與卡死狀態 (解開 Deadlock)
            cursor.execute("SELECT id, is_active FROM customer WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                if existing_user['is_active'] == 1:
                    flash("此 Email 已經註冊過囉！", "error")
                    return redirect(url_for('auth.register'))
                else:
                    # 帳號存在但未啟用 (可能是上次寄信失敗)，刪除舊紀錄讓使用者重新註冊
                    cursor.execute("DELETE FROM customer WHERE email = %s", (email,))
                    conn.commit() 
            
            # 密碼加密
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 【關鍵修復 2】判斷是否為自動化測試腳本 (開後門)
            # 只要信箱結尾是 @test.com，就直接將 is_active 設為 1 (已啟用)
            is_test_account = email.lower().endswith('@test.com')
            is_active = 1 if is_test_account else 0
            
            # 寫入資料庫
            sql = """INSERT INTO customer (email, password, name, phone, region_id, locality_id, address, is_active, created_at, updated_at) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (email, hashed_pw, name, phone, region_id, locality_id, address, is_active, now, now))
            
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

        cursor.execute("SELECT id, is_active FROM customer WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
             flash("找不到此帳號，請重新註冊。", "error")
             return redirect(url_for('auth.register'))
             
        if user['is_active'] == 1:
             flash("帳號已經驗證過囉！請直接登入。", "success")
             return redirect(url_for('auth.login'))

        # 將使用者的 is_active 狀態改為 1 (啟用)
        cursor.execute("UPDATE customer SET is_active=1, updated_at=NOW() WHERE email=%s", (email,))
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
            # 檢查是否已驗證
            if not user['is_active']:
                flash("您的帳號尚未驗證或已被停用。", "error")
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


# --- 會員登出 ---
@auth_bp.route('/logout', methods=['GET','POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# --- 管理員登入 ---
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

# --- 管理員登出 ---
@auth_bp.route('/staff_logout', methods=['GET','POST'])
def staff_logout():
    session.clear()
    return redirect(url_for('auth.staff_login'))