import pytest
from app.db import get_db_connection

def test_reproduce_empty_order_shipping(client, auth_staff, test_order):
    """測試出貨空訂單問題 (已修復：空訂單應自動刪除)"""
    # 確保訂單是 pending
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'pending' WHERE id = %s", (test_order['order_id'],))
    conn.commit()
    cursor.close()
    conn.close()

    # 1. 移除訂單中所有項目
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM order_item WHERE order_id = %s", (test_order['order_id'],))
    items = cursor.fetchall()
    cursor.close()
    conn.close()

    for item in items:
        # 使用 staff/order/edit 移除項目
        response = client.post(f'/staff/order/edit/{test_order["order_id"]}', data={'item_id': item['id']}, follow_redirects=True)
        assert response.status_code == 200
    
    # 確認訂單已被刪除
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM orders WHERE id = %s", (test_order['order_id'],))
    order_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    assert order_count == 0

    # 2. 測試出貨 (若已刪除則無法進行出貨，測試此情境已變得較複雜，
    # 但已證實核心邏輯：訂單會自動刪除)

