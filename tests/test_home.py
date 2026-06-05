import pytest
from app.db import get_db_connection
from datetime import datetime

def test_product_view(client, test_product):
    """測試商品詳情頁顯示"""
    response = client.get(f'/product/{test_product["product_id"]}')
    assert response.status_code == 200
    assert "測試商品" in response.get_data(as_text=True)

def test_add_to_cart(client, test_product):
    """測試加入購物車"""
    # 需先登入
    client.post('/auth/register', data={
        'email': 'cart@test.com', 'password': 'password', 'confirm_password': 'password', 'name': 'Cart User'
    })
    client.post('/auth/login', data={'email': 'cart@test.com', 'password': 'password'})
    
    response = client.post('/checkout/add_to_cart', data={
        'sku_id': test_product['sku_id'],
        'qty': 2
    })
    assert response.status_code == 200
    assert response.json['success'] is True
    
    # 驗證購物車頁面
    response = client.get('/checkout/view_cart')
    assert "測試商品" in response.get_data(as_text=True)
    assert "2" in response.get_data(as_text=True)

def test_full_checkout_flow(client, test_product):
    """測試完整結帳流程"""
    # 1. 登入
    client.post('/auth/register', data={
        'email': 'checkout@test.com', 'password': 'password', 'confirm_password': 'password', 'name': 'Checkout User'
    })
    client.post('/auth/login', data={'email': 'checkout@test.com', 'password': 'password'})
    
    # 2. 加入購物車
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    
    # 3. 填寫配送資訊 (需確保 region 存在，conftest 已初始化)
    response = client.post('/checkout/information', data={
        'name': '收件人',
        'phone': '0912345678',
        'region': '臺北市',
        'locality': '中正區',
        'address': '測試地址 123 號',
        'promo_code': ''
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # 4. 付款頁面
    response = client.post('/checkout/payment', data={
        'card_number': '1234567812345678'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    # 5. 確認訂單並送出
    response = client.post('/checkout/place_order', follow_redirects=True)
    assert response.status_code == 200
    assert "訂單已完成" in response.get_data(as_text=True) or "complete" in response.request.path
    
    # 驗證資料庫訂單與庫存
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1")
    order = cursor.fetchone()
    assert order is not None
    assert order['total'] > 0
    
    # 檢查庫存是否扣除 (原本 10 - 1 = 9)
    cursor.execute("SELECT stock FROM sku WHERE id = %s", (test_product['sku_id'],))
    sku = cursor.fetchone()
    assert sku['stock'] == 9
    
    cursor.close()
    conn.close()
