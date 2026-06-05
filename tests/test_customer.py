import pytest
from app.db import get_db_connection
from datetime import datetime

@pytest.fixture
def auth_customer(client):
    """建立並登入一個測試會員，使用唯一 Email 避免衝突"""
    email = f'user_{datetime.now().timestamp()}@test.com'
    password = 'password'
    client.post('/auth/register', data={
        'email': email, 'password': password, 'confirm_password': password, 'name': 'Profile User'
    })
    client.post('/auth/login', data={'email': email, 'password': password})
    return {'email': email, 'password': password}

def test_profile_edit(client, auth_customer):
    """測試修改會員資料"""
    response = client.post('/customer/profile/edit', data={
        'name': 'Updated Name',
        'phone': '0988777666',
        'region': '臺北市',
        'locality': '大安區',
        'address': '更新後的地址 456 號'
    }, follow_redirects=True)
    
    assert "更新成功" in response.get_data(as_text=True)
    
    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, phone FROM customer WHERE email = %s", (auth_customer['email'],))
    user = cursor.fetchone()
    assert user['name'] == 'Updated Name'
    assert user['phone'] == '0988777666'
    cursor.close()
    conn.close()

def test_order_list_view(client, auth_customer, test_product):
    """測試查看訂單列表與詳情"""
    # 1. 先下一單 (模擬結帳，修正：需先加入購物車，並包含 selected_skus)
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    client.post('/checkout/information', data={
        'selected_skus': [str(test_product['sku_id'])],
        'name': '收件人', 'phone': '0912345678', 'region': '臺北市', 'locality': '中正區', 'address': '測試地址 123 號'
    }, follow_redirects=True)
    client.post('/checkout/payment', data={'card_number': '1234567812345678'}, follow_redirects=True)
    client.post('/checkout/place_order', follow_redirects=True)
    
    # 2. 獲取訂單 ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1")
    order_data = cursor.fetchone()
    assert order_data is not None
    order_id = order_data['id']
    cursor.close()
    conn.close()
    
    # 3. 測試列表頁
    response = client.get('/customer/order/list')
    assert response.status_code == 200
    assert str(order_id) in response.get_data(as_text=True)
    
    # 4. 測試詳情頁
    response = client.get(f'/customer/order/view/{order_id}')
    assert response.status_code == 200
    assert "測試商品" in response.get_data(as_text=True)

def test_change_password(client, auth_customer):
    """測試修改密碼"""
    response = client.post('/customer/profile/password', data={
        'old_password': 'password',
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    }, follow_redirects=True)
    
    # 修改斷言內容以匹配 flash 訊息 (包含驚嘆號)
    assert "密碼修改成功" in response.get_data(as_text=True)
    
    # 嘗試用舊密碼登入應失敗
    client.get('/auth/logout', follow_redirects=True)
    response = client.post('/auth/login', data={
        'email': auth_customer['email'],
        'password': 'password'
    }, follow_redirects=True)
    assert "密碼錯囉" in response.get_data(as_text=True)
    
    # 嘗試用新密碼登入應成功
    response = client.post('/auth/login', data={
        'email': auth_customer['email'],
        'password': 'newpassword123'
    }, follow_redirects=True)
    assert "會員中心" in response.get_data(as_text=True)
