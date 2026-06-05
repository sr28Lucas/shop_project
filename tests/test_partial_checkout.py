import pytest
from app.db import get_db_connection

def test_partial_checkout_flow(client, test_product):
    """測試部分商品結帳流程"""
    # 1. 建立兩個商品
    # (test_product 已建立一個，我們再手動建立一個)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT variant_id FROM sku WHERE id = %s", (test_product['sku_id'],))
    v_id = cursor.fetchone()['variant_id']
    
    cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())",
                   (v_id, 'SKU-EXTRA', 'L', 2000, 1000, 5, 1))
    sku_id_2 = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    # 2. 登入並加入兩個商品到購物車
    email = 'partial@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Partial User'})
    client.post('/auth/login', data={'email': email, 'password': 'password'})
    
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    client.post('/checkout/add_to_cart', data={'sku_id': sku_id_2, 'qty': 1})
    
    # 3. 模擬勾選其中一個商品 (sku_id_2) 進行結帳
    response = client.post('/checkout/information', data={
        'selected_skus': [str(sku_id_2)], # 僅勾選第二個商品
        'name': '收件人',
        'phone': '0912345678',
        'region': '臺北市',
        'locality': '中正區',
        'address': '測試地址 123 號'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # 4. 付款
    client.post('/checkout/payment', data={'card_number': '1234567812345678'}, follow_redirects=True)
    
    # 5. 確認下單
    client.post('/checkout/place_order', follow_redirects=True)
    
    # 6. 驗證訂單內容 (應只有 sku_id_2)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1")
    order = cursor.fetchone()
    
    cursor.execute("SELECT sku_id FROM order_item WHERE order_id = %s", (order['id'],))
    items = cursor.fetchall()
    assert len(items) == 1
    assert items[0]['sku_id'] == sku_id_2
    
    # 7. 驗證購物車 (應保留第一個商品 sku_id)
    cursor.execute("SELECT id FROM cart WHERE customer_id = (SELECT id FROM customer WHERE email = %s)", (email,))
    cart = cursor.fetchone()
    assert cart is not None
    
    cursor.execute("SELECT sku_id FROM cart_item WHERE cart_id = %s", (cart['id'],))
    remaining_items = cursor.fetchall()
    assert len(remaining_items) == 1
    assert remaining_items[0]['sku_id'] == test_product['sku_id']
    
    cursor.close()
    conn.close()
