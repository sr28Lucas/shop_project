import pytest
from app.db import get_db_connection

def test_inventory_deduction(client, auth_client, test_product):
    """測試下單後庫存是否正確扣除"""
    sku_id = test_product['sku_id']
    
    # 1. 取得初始庫存
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT stock FROM sku WHERE id = %s", (sku_id,))
    initial_stock = cursor.fetchone()['stock']
    cursor.close()
    conn.close()
    
    # 2. 登入並下單
    email = 'test@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Buyer'})
    auth_client.login_customer(email=email)

    client.post('/checkout/add_to_cart', data={'sku_id': sku_id, 'qty': 2})
    
    with client.session_transaction() as sess:
        sess['selected_sku_ids'] = [sku_id]
    
    client.post('/checkout/information', data={
        'selected_skus': [str(sku_id)],
        'name': '測試', 'phone': '0912345678', 'region': '臺北市', 'locality': '中正區', 'address': '測試'
    }, follow_redirects=True)
    client.post('/checkout/payment', data={'card_number': '1234567812345678'}, follow_redirects=True)
    response = client.post('/checkout/place_order', follow_redirects=True)
    assert response.status_code == 200
    # Debug
    if "完成訂單" not in response.get_data(as_text=True) and "感謝您的訂單" not in response.get_data(as_text=True):
        print(response.get_data(as_text=True))

    assert "完成訂單" in response.get_data(as_text=True) or "感謝您的訂單" in response.get_data(as_text=True)
    
    # 3. 檢查扣除後庫存
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT stock FROM sku WHERE id = %s", (sku_id,))
    final_stock = cursor.fetchone()['stock']
    cursor.close()
    conn.close()
    
    assert final_stock == initial_stock - 2
