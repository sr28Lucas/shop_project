import pytest
from app.db import get_db_connection
from unittest.mock import patch
from datetime import datetime

@pytest.fixture
def logged_in_staff(client):
    """模擬登入具備 'orders' 權限的管理員"""
    # 建立員工並授予 orders 權限
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 建立角色
    cursor.execute("INSERT INTO role (name, orders, created_at, updated_at) VALUES ('TestRole', 1, NOW(), NOW())")
    role_id = cursor.lastrowid
    
    # 建立員工
    cursor.execute("INSERT INTO staff (email, password, name, role_id, created_at, updated_at) VALUES ('staff@test.com', 'password', 'Test Staff', %s, NOW(), NOW())", (role_id,))
    staff_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    # 模擬 Session
    with client.session_transaction() as sess:
        sess['staff_id'] = staff_id
        
    yield {'staff_id': staff_id}
    
    # 清理
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM staff WHERE id = %s", (staff_id,))
    cursor.execute("DELETE FROM role WHERE id = %s", (role_id,))
    conn.commit()
    cursor.close()
    conn.close()

def test_order_list_access(client, logged_in_staff):
    """測試訂單管理列表存取"""
    with patch('app.blueprints.staff.permission.check_permission', return_value=True):
        response = client.get('/staff/order/list')
    assert response.status_code == 200
    assert "出貨管理" in response.get_data(as_text=True)

def test_order_history_access(client, logged_in_staff):
    """測試訂單歷史頁面存取"""
    with patch('app.blueprints.staff.permission.check_permission', return_value=True):
        response = client.get('/staff/order/history')
    assert response.status_code == 200
    assert "訂單歷史" in response.get_data(as_text=True)
