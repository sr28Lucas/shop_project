import pytest
from app.db import get_db_connection
from datetime import datetime

def test_full_checkout_flow_with_review(client, test_product):
    """測試完整結帳流程，包含：加入購物車 -> 填寫資訊 -> 付款 -> 確認頁面 -> 完成"""
    # 1. 註冊並登入
    unique_email = f"buyer_{datetime.now().timestamp()}@test.com"
    client.post('/auth/register', data={
        'email': unique_email, 'password': 'password', 'confirm_password': 'password', 'name': 'Buyer'
    }, follow_redirects=True)
    client.post('/auth/login', data={'email': unique_email, 'password': 'password'}, follow_redirects=True)
    
    # 2. 加入購物車
    client.post('/checkout/add_to_cart', data={'sku_id': str(test_product['sku_id']), 'qty': '2'})
    
    # 3. 填寫資訊 (POST) -> 預期導向付款頁面
    response = client.post('/checkout/information', data={
        'selected_skus': [str(test_product['sku_id'])],
        'name': '測試者',
        'phone': '0912345678',
        'region': '北部',
        'locality': '臺北市',
        'address': '測試路 123 號'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "付款資訊" in response.get_data(as_text=True)
    
    # 4. 填寫付款資訊 (POST) -> 預期導向確認下單頁面 (place_order GET)
    response = client.post('/checkout/payment', data={
        'card_number': '1234567812345678',
        'cvv': '123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "訂單總檢查" in response.get_data(as_text=True)
    assert "測試者" in response.get_data(as_text=True)
    
    # 5. 確認下單 (POST) -> 預期導向完成頁面
    response = client.post('/checkout/place_order', follow_redirects=True)
    assert response.status_code == 200
    assert "感謝您的訂購" in response.get_data(as_text=True)
    assert "訂單編號" in response.get_data(as_text=True)

    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1")
    order = cursor.fetchone()
    assert order['name'] == '測試者'
    assert order['total'] > 0
    
    cursor.close()
    conn.close()

def test_variant_edit_sku_soft_delete(client, auth_staff, test_product):
    """驗證編輯款式時，未提交的 SKU 應被軟刪除 (is_deleted=1)"""
    product_id = test_product['product_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM variant WHERE product_id = %s LIMIT 1", (product_id,))
    variant_id = cursor.fetchone()['id']
    
    # 建立兩個測試 SKU
    cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, is_deleted, created_at, updated_at) VALUES (%s, 'SKU-A', 'S', 100, 50, 5, 1, 0, NOW(), NOW())", (variant_id,))
    sku_id_a = cursor.lastrowid
    cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, is_deleted, created_at, updated_at) VALUES (%s, 'SKU-B', 'M', 100, 50, 5, 1, 0, NOW(), NOW())", (variant_id,))
    sku_id_b = cursor.lastrowid
    conn.commit()
    
    # 模擬編輯，只提交 SKU-A，不提交 SKU-B
    client.post(f'/staff/product/{product_id}/variant/{variant_id}/edit', data={
        'color': '紅色',
        'variant_is_active': 'on',
        'sku_id[]': [str(sku_id_a)],
        'sku_code[]': ['SKU-A'],
        'size[]': ['S'],
        'price[]': ['100'],
        'cost[]': ['50'],
        'stock[]': ['5'],
        'is_active[]': ['0'] # 代表第一個 SKU 被選中
    }, follow_redirects=True)
    
    # 驗證 SKU-B 的狀態
    cursor.execute("SELECT is_active, is_deleted FROM sku WHERE id = %s", (sku_id_b,))
    sku_b = cursor.fetchone()
    assert sku_b['is_deleted'] == 1
    assert sku_b['is_active'] == 0
    
    cursor.close()
    conn.close()

def test_promo_code_usage_increment(client, test_product):
    """驗證下單成功後，優惠碼使用次數會增加"""
    # 1. 建立測試優惠碼
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("INSERT INTO promo_code (code, discount_type, discount_value, min_order_amount, used_count, is_active, is_deleted, created_at, updated_at) VALUES ('TESTPROMO', 'subtotal_deduction', 100, 0, 0, 1, 0, NOW(), NOW())")
    promo_id = cursor.lastrowid
    conn.commit()
    
    # 2. 登入並下單
    unique_email = f"buyer_promo_{datetime.now().timestamp()}@test.com"
    client.post('/auth/register', data={'email': unique_email, 'password': 'password', 'confirm_password': 'password', 'name': 'PromoBuyer'}, follow_redirects=True)
    client.post('/auth/login', data={'email': unique_email, 'password': 'password'}, follow_redirects=True)
    client.post('/checkout/add_to_cart', data={'sku_id': str(test_product['sku_id']), 'qty': '1'})
    client.post('/checkout/information', data={
        'selected_skus': [str(test_product['sku_id'])],
        'name': '測試者', 'phone': '0912345678', 'region': '北部', 'locality': '臺北市', 'address': '測試路 123 號',
        'promo_code': 'TESTPROMO'
    }, follow_redirects=True)
    client.post('/checkout/payment', data={'card_number': '1234567812345678', 'cvv': '123'}, follow_redirects=True)
    client.post('/checkout/place_order', follow_redirects=True)
    
    # 3. 驗證使用次數
    cursor.execute("SELECT used_count FROM promo_code WHERE id = %s", (promo_id,))
    promo = cursor.fetchone()
    assert promo['used_count'] == 1
    
    cursor.close()
    conn.close()

def test_analytics_page_access(client, auth_staff):
    """驗證後台潛力商品分析頁面可正常存取"""
    response = client.get('/staff/product/analytics/hot-items', follow_redirects=True)
    assert response.status_code == 200
    # 檢查頁面關鍵字
    assert "潛力商品數據分析" in response.get_data(as_text=True)
