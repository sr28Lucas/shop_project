import pytest
import os
import json
import mysql.connector
from datetime import datetime
from app import create_app
from app.config import config
from app.db import get_db_connection
from flask_bcrypt import Bcrypt

# 測試資料庫名稱
TEST_DB_NAME = 'shop_test'

def initialize_test_data(conn):
    cursor = conn.cursor(dictionary=True)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    bcrypt = Bcrypt()

    # 1. 建立 root 角色與帳號 (參考 setup.py)
    email = 'root@root'
    password = 'root'
    name = 'root'
    rolename = 'root'
    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        # 建立角色
        sql_role = """
                INSERT INTO role (name, member, orders, product, inquiry, statistic, staff, announcement, `return`, promo, created_at, updated_at)
                VALUES (%s, 1, 1, 1, 1, 1, 1, 1, 1, 1, %s, %s)            
                """
        cursor.execute(sql_role, (rolename, now, now))
        role_id = cursor.lastrowid

        # 建立管理員
        sql_admin = """
                    INSERT INTO staff (email, password, name, role_id, created_at, updated_at) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
        cursor.execute(sql_admin, (email, hashed_pw, name, role_id, now, now))

        # 2. 自動匯入地區與運費 (參考 setup.py)
        json_path = os.path.join(config.BASE_DIR, 'app', 'static', 'json', 'taiwan_districts.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for city, info in data.items():
                    cursor.execute("INSERT INTO region (name, fee, created_at, updated_at) VALUES (%s, %s, %s, %s)", 
                                   (city, info['fee'], now, now))
                    region_id = cursor.lastrowid
                    for district in info['districts']:
                        cursor.execute("INSERT INTO locality (region_id, name) VALUES (%s, %s)", 
                                       (region_id, district))
        
        # 3. 建立預設分類
        cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES (%s, %s, %s)", ("預設分類", now, now))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Test data initialization failed: {e}")
    finally:
        cursor.close()

@pytest.fixture(scope='session', autouse=True)
def db_setup():
    # 讀取原本的配置
    admin_config = config.DB_CONFIG.copy()
    # 移除 database 以便連線到 MySQL Server
    admin_config.pop('database', None)
    
    # 建立測試資料庫
    try:
        conn = mysql.connector.connect(**admin_config)
        cursor = conn.cursor()
        cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        cursor.execute(f"CREATE DATABASE {TEST_DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        conn.close()
    except Exception as e:
        pytest.exit(f"Could not create test database: {e}")

    # 修改全域 config 以指向測試資料庫
    config.DB_CONFIG['database'] = TEST_DB_NAME

    # 匯入結構
    conn = get_db_connection()
    cursor = conn.cursor()
    sql_file = os.path.join(config.BASE_DIR, 'latest_資料庫系統_電商網站_20260603.sql')
    
    if os.path.exists(sql_file):
        with open(sql_file, 'r', encoding='utf-8') as f:
            # 簡單的分隔 SQL 指令 (處理註解與多行)
            sql_script = f.read()
            # 移除 SQL 註解
            import re
            sql_script = re.sub(r'/\*.*?\*/', '', sql_script, flags=re.DOTALL)
            sql_script = re.sub(r'--.*', '', sql_script)
            
            commands = sql_script.split(';')
            for command in commands:
                if command.strip():
                    try:
                        cursor.execute(command)
                    except Exception as e:
                        print(f"Error in SQL: {e}\nCommand: {command[:100]}")
        conn.commit()
    
    # 初始化資料
    initialize_test_data(conn)
    cursor.close()
    conn.close()

    yield

    # 測試結束後可選擇不刪除，方便檢查，或在此刪除
    # conn = mysql.connector.connect(**admin_config)
    # cursor = conn.cursor()
    # cursor.execute(f"DROP DATABASE {TEST_DB_NAME}")
    # cursor.close()
    # conn.close()

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False, # 測試時關閉 CSRF
        "SERVER_NAME": "localhost.localdomain" # 避免 url_for 報錯
    })
    # 清除 session
    with app.test_request_context():
        from flask import session
        session.clear()
    
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """提供一個模擬登入後的 Helper"""
    class AuthHelper:
        def login_customer(self, email='test@test.com', password='password'):
            return client.post('/auth/login', data={
                'email': email,
                'password': password
            }, follow_redirects=True)

        def login_staff(self, email='root@root', password='root'):
            return client.post('/auth/staff_login', data={
                'email': email,
                'password': password
            }, follow_redirects=True)
            
    return AuthHelper()

@pytest.fixture
def auth_staff(client):
    """登入管理員 (預設 root)"""
    client.post('/auth/staff_login', data={'email': 'root@root', 'password': 'root'})
    return {'email': 'root@root'}

@pytest.fixture
def staff_factory(client):
    """動態建立具備特定權限的員工工廠"""
    def _create_staff(role_name, permissions=None):
        if permissions is None:
            permissions = {}
        
        # 預設權限全為 0
        perms = {
            'member': 0, 'orders': 0, 'product': 0, 'inquiry': 0, 
            'statistic': 0, 'staff': 0, 'announcement': 0, 
            'return': 0, 'promo': 0
        }
        perms.update(permissions)
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. 建立角色
        cursor.execute("""
            INSERT INTO role (name, member, orders, product, inquiry, statistic, staff, announcement, `return`, promo, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (role_name, perms['member'], perms['orders'], perms['product'], perms['inquiry'], 
              perms['statistic'], perms['staff'], perms['announcement'], perms['return'], perms['promo'], now, now))
        role_id = cursor.lastrowid
        
        # 2. 建立員工
        email = f"{role_name.lower()}@test.com"
        password = "password"
        from flask_bcrypt import Bcrypt
        hashed_pw = Bcrypt().generate_password_hash(password).decode('utf-8')
        
        cursor.execute("""
            INSERT INTO staff (email, password, name, role_id, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (email, hashed_pw, f"Staff {role_name}", role_id, now, now))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {'email': email, 'password': password, 'role_name': role_name}
    
    return _create_staff

@pytest.fixture
def test_order(client, test_product):
    """建立一個已完成的測試訂單供退貨/工作流測試"""
    # Helper for unique IDs
    def gen_unique_id():
        return datetime.now().timestamp()
    
    # 登入
    email = f'buyer_{gen_unique_id()}@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Buyer'})
    client.post('/auth/login', data={'email': email, 'password': 'password'})
    
    # 下單 (修正：需先加入購物車，並包含 selected_skus)
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    client.post('/checkout/information', data={
        'selected_skus': [str(test_product['sku_id'])],
        'name': '收件人', 'phone': '0912345678', 'region': '臺北市', 'locality': '中正區', 'address': '測試地址 123 號'
    }, follow_redirects=True)
    client.post('/checkout/payment', data={'card_number': '1234567812345678'}, follow_redirects=True)
    client.post('/checkout/place_order', follow_redirects=True)
    
    # 取得訂單 ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1")
    order = cursor.fetchone()
    # 模擬訂單狀態為已完成
    cursor.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (order['id'],))
    conn.commit()
    
    # 取得訂單項目 ID
    cursor.execute("SELECT id FROM order_item WHERE order_id = %s", (order['id'],))
    item = cursor.fetchone()
    
    cursor.close()
    conn.close()
    return {'order_id': order['id'], 'item_id': item['id']}
@pytest.fixture
def test_product(db_setup):
    """建立測試商品資料，並確保不重複建立"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 檢查分類是否存在
    cursor.execute("SELECT id FROM category WHERE name = %s", ('測試分類',))
    cat = cursor.fetchone()
    if cat:
        cat_id = cat['id']
    else:
        cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES (%s, %s, %s)", ('測試分類', now, now))
        cat_id = cursor.lastrowid
    
    # 建立商品
    cursor.execute("INSERT INTO product (category_id, name, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)", 
                   (cat_id, f'測試商品_{datetime.now().timestamp()}', 1, now, now))
    p_id = cursor.lastrowid
    
    # 建立變體
    cursor.execute("INSERT INTO variant (product_id, color, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)", 
                   (p_id, '藍色', 1, now, now))
    v_id = cursor.lastrowid
    
    # 建立 SKU
    sku_code = f'SKU-{datetime.now().timestamp()}'
    cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                   (v_id, sku_code, 'M', 1000, 500, 10, 1, now, now))
    sku_id = cursor.lastrowid
    
    conn.commit()
    cursor.close()
    conn.close()
    return {'sku_id': sku_id, 'product_id': p_id, 'sku_code': sku_code}
