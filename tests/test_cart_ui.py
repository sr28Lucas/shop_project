import pytest
from app.db import get_db_connection

@pytest.fixture
def logged_in_customer(client):
    """註冊並登入一個測試會員"""
    email = 'cart_user@test.com'
    password = 'password'
    client.post('/auth/register', data={
        'email': email,
        'password': password,
        'confirm_password': password,
        'name': 'Cart User'
    }, follow_redirects=True)
    client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)
    return email, password

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
    cursor.execute("DELETE FROM cart_item WHERE sku_id = %s", (sku_id,))
    cursor.execute("DELETE FROM sku WHERE id = %s", (sku_id,))
    cursor.execute("DELETE FROM variant WHERE id = %s", (var_id,))
    cursor.execute("DELETE FROM product WHERE id = %s", (prod_id,))
    cursor.execute("DELETE FROM category WHERE id = %s", (cat_id,))
    conn.commit()
    cursor.close()
    conn.close()

def test_view_cart_empty(client, logged_in_customer):
    """測試購物車為空時的渲染"""
    response = client.get('/checkout/view_cart', follow_redirects=True)
    assert response.status_code == 200
    assert "購物車目前是空的" in response.get_data(as_text=True)

def test_view_cart_with_items(client, logged_in_customer, test_sku):
    """測試購物車有商品時的渲染"""
    # 1. 加入商品
    client.post('/checkout/add_to_cart', data={'sku_id': test_sku, 'qty': 2})
    
    # 2. 存取購物車
    response = client.get('/checkout/view_cart', follow_redirects=True)
    assert response.status_code == 200
    
    data = response.get_data(as_text=True)
    assert "我的購物車" in data
    assert "NT$" in data
    assert "前往結帳" in data
