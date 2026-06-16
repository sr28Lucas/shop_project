from flask import Flask, session, request, redirect, url_for, flash
from .extensions import bcrypt
from .config import config
from app.db import get_db_connection


def create_app():
    # 1. 建立 Flask 實例
    app = Flask(__name__)
    # 2. 載入設定 (從 config.py 讀取不同環境的設定)
    app.config.from_object(config) # 自動將config中全大寫的屬性導入

    # ==========================================
    # 【新增】加入 Email 伺服器設定 (以 Gmail 為例)
    # ==========================================
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'alansu20051010@gmail.com'  # 🛑 記得換成你的 Gmail
    app.config['MAIL_PASSWORD'] = 'mfvp atnh qols hykc'    # 🛑 記得換成 Google 的 16 位數應用程式密碼
    app.config['MAIL_DEFAULT_SENDER'] = 'alansu20051010@gmail.com' # 🛑 記得換成你的 Gmail
    
    # 3. 初始化插件 (將插件繫結到 app)
    bcrypt.init_app(app)

    
    # ==========================================
    # 【新增】綁定 Mail 套件到 app
    # ==========================================
    from .blueprints.auth import mail 
    mail.init_app(app)
    
    # db.init_app(app)
    # migrate.init_app(app, db)
    # login_manager.init_app(app)
    # csrf.init_app(app)

    # 4. 註冊藍圖 (Blueprints) - 電商模組化關鍵
    from .blueprints.auth import auth_bp
    from .blueprints.staff import staff_bp
    from .blueprints.customer import customer_bp
    from .blueprints.home import home_bp


    # app.register_blueprint(image_bp, url_prefix='/image') #使圖片可路由
    app.register_blueprint(auth_bp, url_prefix='/auth') #登入功能
    app.register_blueprint(staff_bp, url_prefix="/staff") #管理員儀錶板 儀錶板裡的功能註冊在staff.__init__.py裡才能延續前綴 不要註冊在這 
    app.register_blueprint(customer_bp, url_prefix='/customer') #會員中心 
    app.register_blueprint(home_bp, url_prefix='/') #主頁

    # 5. 全域帳號狀態檢查
    @app.before_request
    def check_account_status():
        # 排除登入、註冊、靜態資源、登出路徑
        if request.endpoint and (
            request.endpoint.startswith('auth.') or 
            request.endpoint.startswith('static')
        ):
            return

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 檢查客戶
        if 'customer_id' in session:
            cursor.execute("SELECT is_active FROM customer WHERE id = %s", (session['customer_id'],))
            user = cursor.fetchone()
            if not user or not user['is_active']:
                session.clear()
                flash("您的帳號已被停用，請聯絡管理員。", "error")
                cursor.close()
                conn.close()
                return redirect(url_for('auth.login'))

        # 檢查員工
        if 'staff_id' in session:
            cursor.execute("SELECT is_active FROM staff WHERE id = %s", (session['staff_id'],))
            user = cursor.fetchone()
            if not user or not user['is_active']:
                session.clear()
                flash("您的員工帳號已被停用，請聯絡系統管理員。", "error")
                cursor.close()
                conn.close()
                return redirect(url_for('auth.staff_login'))

        cursor.close()
        conn.close()

    # 6. 全域 context processor，在所有頁面顯示購物車數量
    @app.context_processor
    def inject_cart_count():
        if 'customer_id' in session:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(qty) FROM cart_item ci
                JOIN cart c ON ci.cart_id = c.id
                WHERE c.customer_id = %s
            """, (session['customer_id'],))
            result = cursor.fetchone()
            count = result[0] if result and result[0] else 0
            cursor.close()
            conn.close()
            return dict(cart_count=count)
        return dict(cart_count=0)

    return app



if __name__ == '__main__':
    c = config
    print(c.DB_CONFIG)