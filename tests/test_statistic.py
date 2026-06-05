import pytest
from app.db import get_db_connection
from datetime import datetime

def setup_order(client, test_product, status='completed'):
    # Login as buyer
    email = f'buyer_{datetime.now().timestamp()}@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Buyer'})
    client.post('/auth/login', data={'email': email, 'password': 'password'})
    
    # Add to cart
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    
    # Place order
    client.post('/checkout/information', data={
        'selected_skus': [str(test_product['sku_id'])],
        'name': '收件人', 'phone': '0912345678', 'region': '臺北市', 'locality': '中正區', 'address': '測試地址 123 號'
    }, follow_redirects=True)
    client.post('/checkout/payment', data={'card_number': '1234567812345678'}, follow_redirects=True)
    client.post('/checkout/place_order', follow_redirects=True)
    
    # Update status
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1")
    order = cursor.fetchone()
    cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    return order['id']

def test_statistic_revenue_access(client, auth_staff):
    """測試營收統計頁面存取"""
    response = client.get('/staff/statistic/revenue')
    assert response.status_code == 200
    assert "營收" in response.get_data(as_text=True)

def test_statistic_sales_access(client, auth_staff):
    """測試銷售統計頁面存取"""
    response = client.get('/staff/statistic/sales')
    assert response.status_code == 200
    assert "銷售" in response.get_data(as_text=True)

def test_statistic_calculations(client, auth_staff, test_product):
    """測試營收統計頁面顯示數據是否正確"""
    
    # 建立一個已完成訂單 (假設金額為 1000)
    setup_order(client, test_product, status='completed')
    
    # 建立一個待出貨訂單
    setup_order(client, test_product, status='pending')
    
    # 建立一個已退款訂單
    setup_order(client, test_product, status='refunded')
    
    # 查詢統計
    response = client.get('/staff/statistic/revenue')
    assert response.status_code == 200
    
    content = response.get_data(as_text=True)
    
    # 驗證統計值
    assert "總營收" in content
    assert "$1000" in content or "$1000.00" in content
    assert "有效訂單數" in content
    # 有一個 completed，所以有效訂單應該是 1 (假設定義為 completed)
    assert ">1</div>" in content 
    
    assert "待出貨訂單" in content
    assert ">1</div>" in content
    
    assert "已退款訂單" in content
    assert ">1</div>" in content
