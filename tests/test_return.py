import pytest
from app.db import get_db_connection
from datetime import datetime

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
