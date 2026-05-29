from flask import Flask
from .extensions import bcrypt
from .config import config


def create_app():
    # 1. 建立 Flask 實例
    app = Flask(__name__)
    # 2. 載入設定 (從 config.py 讀取不同環境的設定)
    app.config.from_object(config) # 自動將config中全大寫的屬性導入

    # 3. 初始化插件 (將插件繫結到 app)
    bcrypt.init_app(app)

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
    app.register_blueprint(staff_bp, url_prefix="/staff") #管理員儀錶板 儀錶板裡的功能註冊在dashboard.py裡才能延續前綴 不要註冊在這 
    app.register_blueprint(customer_bp, url_prefix='/customer') #會員中心 
    app.register_blueprint(home_bp, url_prefix='/') #主頁

    # 5. 這裡可以放置全域的 context processor (例如在所有頁面顯示購物車數量)
    # @app.context_processor
    # def inject_cart_count():
    #     # 假設你有一個獲取購物車數量的函式
    #     return dict(cart_count=7) 

    return app



if __name__ == '__main__':
    c = config
    print(c.DB_CONFIG)

