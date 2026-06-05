import pytest
from app.db import get_db_connection

def test_ajax_add_to_cart_response(client, test_product):
    """測試 AJAX 加入購物車的 JSON 響應格式"""
    client.post('/auth/register', data={'email': 'ajax@test.com', 'password': 'password', 'confirm_password': 'password', 'name': 'Ajax'})
    client.post('/auth/login', data={'email': 'ajax@test.com', 'password': 'password'})
    
    response = client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert "已加入購物車" in data['message']

def test_checkout_session_consistency(client, test_product):
    """
    測試 Session 一致性：
    1. 使用者 A 將商品加入購物車並進入填寫資訊頁面。
    2. 使用者 A 在另一個標籤頁將該商品從購物車移除。
    3. 使用者 A 回到原本標籤頁繼續提交資訊與付款。
    4. 系統應在下單時發現購物車已變動並阻斷。
    """
    email = 'consistency@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Consist'})
    client.post('/auth/login', data={'email': email, 'password': 'password'})
    
    # Step 1: 加入並進入資訊頁
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    client.post('/checkout/information', data={
        'selected_skus': [str(test_product['sku_id'])],
        'name': 'Name', 'phone': '0911222333', 'region': '臺北市', 'locality': '中正區', 'address': 'Address'
    })
    
    # Step 2: 模擬「另一個標籤頁」移除商品
    client.post('/checkout/remove_item', data={'sku_id': test_product['sku_id']})
    
    # Step 3: 回到原本流程進行付款 (此時 session 仍存有 selected_sku_ids)
    client.post('/checkout/payment', data={'card_number': '1111222233334444'})
    
    # Step 4: 執行下單
    response = client.post('/checkout/place_order', follow_redirects=True)
    
    # 預期結果：由於資料庫中的 cart_item 已被刪除，place_order 查不到項目，應跳出錯誤
    assert "您選擇的商品目前無法結帳" in response.get_data(as_text=True)
    assert "/checkout/view_cart" in response.request.path

def test_insufficient_stock_at_place_order(client, test_product):
    """
    測試高並發/庫存變動場景：
    1. 使用者 A 進入結帳最後一步。
    2. 商品庫存被其他人買光或管理員修改。
    3. 使用者 A 點擊下單，系統應阻斷。
    """
    email = 'stock_fail@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Stock'})
    client.post('/auth/login', data={'email': email, 'password': 'password'})
    
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 5})
    client.post('/checkout/information', data={
        'selected_skus': [str(test_product['sku_id'])],
        'name': 'Name', 'phone': '0911222333', 'region': '臺北市', 'locality': '中正區', 'address': 'Address'
    })
    client.post('/checkout/payment', data={'card_number': '1111222233334444'})
    
    # 模擬庫存被改為 0
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sku SET stock = 0 WHERE id = %s", (test_product['sku_id'],))
    conn.commit()
    cursor.close()
    conn.close()
    
    # 點擊下單
    response = client.post('/checkout/place_order', follow_redirects=True)
    assert "庫存不足" in response.get_data(as_text=True)
