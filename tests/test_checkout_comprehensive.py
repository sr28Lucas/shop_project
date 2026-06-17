import pytest
from unittest.mock import patch
from app.db import get_db_connection

@pytest.fixture
def logged_in_client(client, auth_client):
    """協助註冊並登入測試帳號"""
    email = 'test_buyer@test.com'
    password = 'password'
    client.post('/auth/register', data={
        'email': email,
        'password': password,
        'confirm_password': password,
        'name': 'Test Buyer'
    }, follow_redirects=True)
    auth_client.login_customer(email=email, password=password)
    return client

@pytest.fixture
def test_sku():
    """在測試前建立一個測試 SKU，並在測試後清理"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 建立分類
    cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES ('測試分類', NOW(), NOW())")
    cat_id = cursor.lastrowid
    
    # 建立商品
    cursor.execute("INSERT INTO product (category_id, name, is_active, created_at, updated_at) VALUES (%s, '測試商品', 1, NOW(), NOW())", (cat_id,))
    prod_id = cursor.lastrowid
    
    # 建立變體
    cursor.execute("INSERT INTO variant (product_id, color, is_active, created_at, updated_at) VALUES (%s, '紅色', 1, NOW(), NOW())", (prod_id,))
    var_id = cursor.lastrowid
    
    # 建立 SKU (庫存為 10)
    cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, stock, is_active, created_at, updated_at) VALUES (%s, 'TEST-SKU', 'M', 100, 10, 1, NOW(), NOW())", (var_id,))
    sku_id = cursor.lastrowid
    
    conn.commit()
    cursor.close()
    conn.close()
    
    yield sku_id
    
    # 清理資料
    conn = get_db_connection()
    cursor = conn.cursor()
    # 先清理依賴表
    cursor.execute("DELETE FROM cart_item WHERE sku_id = %s", (sku_id,))
    # 再清理主表 (依賴順序)
    cursor.execute("DELETE FROM sku WHERE id = %s", (sku_id,))
    cursor.execute("DELETE FROM variant WHERE id = %s", (var_id,))
    cursor.execute("DELETE FROM product WHERE id = %s", (prod_id,))
    cursor.execute("DELETE FROM category WHERE id = %s", (cat_id,))
    conn.commit()
    cursor.close()
    conn.close()

def test_add_to_cart_success(logged_in_client, test_sku):
    """測試成功加入商品到購物車 (三層驗證標準)"""
    # 1. 操作驗證
    response = logged_in_client.post('/checkout/add_to_cart', data={
        'sku_id': test_sku,
        'qty': 1
    })
    assert response.status_code == 200
    assert response.json['success'] is True
    
    # 2. 資料持久化驗證
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM cart_item WHERE sku_id = %s", (test_sku,))
    cart_item = cursor.fetchone()
    assert cart_item is not None
    assert cart_item['qty'] == 1
    cursor.close()
    conn.close()

    # 3. 前端 UI 渲染驗證
    response_view = logged_in_client.get('/checkout/view_cart', follow_redirects=True)
    assert response_view.status_code == 200
    data = response_view.get_data(as_text=True)
    assert "測試商品" in data # 驗證加入的商品名稱出現在購物車頁面

def test_add_to_cart_insufficient_stock(logged_in_client, test_sku):
    """測試庫存不足時加入失敗"""
    # 庫存為 10，請求 11
    response = logged_in_client.post('/checkout/add_to_cart', data={
        'sku_id': test_sku,
        'qty': 11
    })
    
    assert response.status_code == 400
    assert response.json['success'] is False
    assert "庫存不足" in response.json['message']

def test_view_cart_unauthorized(client):
    """測試未登入存取購物車應重定向至登入頁"""
    response = client.get('/checkout/view_cart', follow_redirects=False)
    assert response.status_code == 302
    assert "login" in response.location
