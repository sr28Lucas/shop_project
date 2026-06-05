import pytest
from app.db import get_db_connection

def test_variant_add(client, auth_staff, test_product):
    """測試後台新增款式"""
    response = client.post(f'/staff/product/{test_product["product_id"]}/variant/add', data={
        'color': '紅色',
        'variant_is_active': 'on',
        'sku_code[]': ['SKU-RED-S'],
        'size[]': ['S'],
        'price[]': ['1200'],
        'cost[]': ['600'],
        'stock[]': ['20'],
        'is_active[]': ['0'] # 對應第一個sku
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "新增變體與規格成功" in response.get_data(as_text=True)

def test_order_status_update(client, auth_staff, test_order):
    """測試訂單出貨流程"""
    # 訂單必須是 pending 才能出貨
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'pending' WHERE id = %s", (test_order['order_id'],))
    conn.commit()
    cursor.close()
    conn.close()
    
    # 測試出貨
    response = client.post(f'/staff/order/ship/{test_order["order_id"]}', follow_redirects=True)
    assert response.status_code == 200
    assert "已確認出貨" in response.get_data(as_text=True)
    
    # 驗證狀態
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM orders WHERE id = %s", (test_order['order_id'],))
    order = cursor.fetchone()
    assert order['status'] == 'shipped'
    cursor.close()
    conn.close()
