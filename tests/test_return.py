import pytest
from app.db import get_db_connection
from datetime import datetime

@pytest.fixture
def test_order(client, test_product):
    """建立一個已完成的測試訂單供退貨測試"""
    # Helper for unique IDs
    def gen_unique_id():
        return datetime.now().timestamp()
    
    # 登入
    email = f'buyer_{gen_unique_id()}@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Buyer'})
    client.post('/auth/login', data={'email': email, 'password': 'password'})
    
    # 下單
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    client.post('/checkout/information', data={
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

def test_return_apply(client, test_order):
    """測試退貨申請流程"""
    response = client.post(f'/customer/return/apply/{test_order["order_id"]}', data={
        'item_ids': [str(test_order['item_id'])],
        f'qty_{test_order["item_id"]}': '1',
        f'reason_{test_order["item_id"]}': '不喜歡',
        'overall_reason': '整體原因'
    }, follow_redirects=True)
    
    assert "退貨申請已送出" in response.get_data(as_text=True)
    
    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM return_request WHERE order_id = %s", (test_order['order_id'],))
    rr = cursor.fetchone()
    assert rr is not None
    assert rr['status'] == 'requested'
    cursor.close()
    conn.close()
