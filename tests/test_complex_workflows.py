import pytest
from app.db import get_db_connection
from datetime import datetime

def test_mega_journey_e2e(client, staff_factory):
    """
    全鏈路綜合測試 (使用 Root 帳號以排除權限干擾)
    """
    # Helper for unique IDs
    import random
    def gen_id():
        return str(random.randint(1000, 9999))

    # --- 1. 管理員建立商品 (使用 Root) ---
    res = client.post('/auth/staff_login', data={'email': 'root@root', 'password': 'root'}, follow_redirects=True)
    assert "儀錶板" in res.get_data(as_text=True)
    
    # 先拿分類
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM category LIMIT 1")
    cat_id = cursor.fetchone()['id']
    cursor.close()
    conn.close()
    
    # 新增商品
    item_name = f"E2E Item {gen_id()}"
    res = client.post('/staff/product/add', data={'name': item_name, 'category_id': cat_id, 'description': 'desc'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"OK" in res.data
    
    # 獲取剛建立的商品 ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM product WHERE name = %s", (item_name,))
    p_data = cursor.fetchone()
    assert p_data is not None
    p_id = p_data['id']
    cursor.close()
    conn.close()
    
    # 建立一個變體與 SKU
    sku_code = f"SKU{gen_id()}"
    res = client.post(f'/staff/product/{p_id}/variant/add', data={
        'color': '銀色', 'variant_is_active': 'on',
        'sku_code[]': [sku_code], 'size[]': ['XL'], 'price[]': ['5000'], 'cost[]': ['2000'], 'stock[]': ['10'], 'is_active[]': ['0']
    }, follow_redirects=True)
    assert "新增變體與規格成功" in res.get_data(as_text=True)
    
    # 使用新連線獲取 SKU ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM sku WHERE sku_code = %s", (sku_code,))
    sku_data = cursor.fetchone()
    assert sku_data is not None, "SKU should be created"
    sku_id = sku_data['id']
    cursor.close()
    conn.close()

    # --- 2. 管理員建立優惠碼 (使用 Root) ---
    promo_code = f"PROMO{gen_id()}"
    res = client.post('/staff/promo/add', data={
        'code': promo_code, 'description': 'E2E Test', 'discount_type': 'subtotal_discount',
        'discount_value': '20', 'usage_limit': '5', 'min_order_amount': '1000',
        'start_at': '', 'end_at': ''
    }, follow_redirects=True)
    assert "折扣碼新增成功" in res.get_data(as_text=True)

    # --- 3. 客戶行為 ---
    client.get('/auth/staff_logout') # 登出員工
    c_email = f"c{gen_id()}@test.com"
    client.post('/auth/register', data={'email': c_email, 'password': 'password', 'confirm_password': 'password', 'name': 'Mega User'})
    client.post('/auth/login', data={'email': c_email, 'password': 'password'})
    
    # 加入願望清單
    client.post(f'/wishlist/toggle/{p_id}')
    
    # 轉入購物車
    client.post('/checkout/add_to_cart', data={'sku_id': sku_id, 'qty': 2})
    
    # 結帳資訊
    res = client.post('/checkout/information', data={
        'selected_skus': [str(sku_id)],
        'name': '收件人', 'phone': '0988000000', 'region': '臺北市', 'locality': '中正區', 'address': '測試結帳地址 789 號',
        'promo_code': promo_code
    }, follow_redirects=True)
    assert "付款資訊" in res.get_data(as_text=True)
    
    # 這裡可能需要確保 session 被正確設定，可以嘗試再次請求結帳頁面以確保 session
    # 或者是直接進行付款，假設 session 已設定。
    
    # 付款
    res = client.post('/checkout/payment', data={'card_number': '4444555566667777'}, follow_redirects=True)
    assert "確認下單" in res.get_data(as_text=True)
    
    # 下單
    res = client.post('/checkout/place_order', follow_redirects=True)
    
    assert "感謝您的訂購！" in res.get_data(as_text=True)
    
    # 使用新連線獲取訂單 ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1")
    order_data = cursor.fetchone()
    assert order_data is not None, "Order should be created successfully"
    order_id = order_data['id']
    cursor.close()
    conn.close()

    # --- 4. 管理員出貨 (再次登入 Root) ---
    client.post('/auth/staff_login', data={'email': 'root@root', 'password': 'root'})
    client.post(f'/staff/order/ship/{order_id}', follow_redirects=True)
    
    # 模擬訂單完成 (才能申請退貨)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (order_id,))
    conn.commit()
    cursor.close()
    conn.close()

    # --- 5. 客戶申請退貨 ---
    client.get('/auth/staff_logout') # 確保登出員工
    client.post('/auth/login', data={'email': c_email, 'password': 'password'})
    
    # 先拿 order_item_id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM order_item WHERE order_id = %s", (order_id,))
    oi_id = cursor.fetchone()['id']
    cursor.close()
    conn.close()
    
    response = client.post(f'/customer/return/apply/{order_id}', data={
        'item_ids': [str(oi_id)],
        f'qty_{oi_id}': '1',
        f'reason_{oi_id}': 'E2E Return Test',
        'overall_reason': 'General'
    }, follow_redirects=True)
    
    assert "退貨申請已送出" in response.get_data(as_text=True)
    
    # --- 6. 最終驗證資料庫 ---
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM return_request WHERE order_id = %s", (order_id,))
    assert cursor.fetchone()['status'] == 'requested'
    cursor.close()
    conn.close()
