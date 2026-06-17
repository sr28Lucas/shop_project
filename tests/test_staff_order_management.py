import pytest
from app.db import get_db_connection
from unittest.mock import patch

from datetime import datetime

@pytest.fixture
def test_order_setup(client, auth_staff):
    """建立一個待出貨的測試訂單"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    unique_email = f'test_customer_{datetime.now().timestamp()}@test.com'
    
    # 建立一個測試用戶
    cursor.execute("INSERT INTO customer (email, password, name) VALUES (%s, 'password', '測試顧客')", (unique_email,))
    customer_id = cursor.lastrowid
    
    # 建立一個訂單
    cursor.execute("""
        INSERT INTO orders (customer_id, name, phone, address, total, status, created_at, updated_at)
        VALUES (%s, '測試收件人', '0912345678', '測試地址', 1000, 'pending', NOW(), NOW())
    """, (customer_id,))
    order_id = cursor.lastrowid
    
    # 建立一個訂單項目
    cursor.execute("INSERT INTO order_item (order_id, product_name, qty, unit_price) VALUES (%s, '測試商品', 1, 1000)", (order_id,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    yield order_id

def test_order_list_access(client, auth_staff):
    """測試出貨管理列表"""
    response = client.get('/staff/order/list')
    assert response.status_code == 200
    assert "出貨管理" in response.get_data(as_text=True)

def test_ship_order_success(client, auth_staff, test_order_setup):
    """測試確認出貨成功"""
    response = client.post(f'/staff/order/ship/{test_order_setup}', follow_redirects=True)
    assert response.status_code == 200
    assert f"訂單 {test_order_setup} 已確認出貨" in response.get_data(as_text=True)

    # 驗證狀態
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE id = %s", (test_order_setup,))
    order = cursor.fetchone()
    assert order['status'] == 'shipped'
    cursor.close()
    conn.close()

def test_cancel_order_success(client, auth_staff, test_order_setup):
    """測試取消訂單成功"""
    response = client.post(f'/staff/order/cancel/{test_order_setup}', follow_redirects=True)
    assert response.status_code == 200
    assert f"訂單 {test_order_setup} 已取消" in response.get_data(as_text=True)

    # 驗證狀態
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE id = %s", (test_order_setup,))
    order = cursor.fetchone()
    assert order['status'] == 'cancelled'
    cursor.close()
    conn.close()
