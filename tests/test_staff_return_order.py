import pytest
from app.db import get_db_connection
from unittest.mock import patch
from datetime import datetime

@pytest.fixture
def logged_in_staff_return(client):
    """模擬登入具備 'return' 權限的管理員"""
    # 建立角色與管理員
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO role (name, `return`, created_at, updated_at) VALUES ('ReturnRole', 1, NOW(), NOW())")
    role_id = cursor.lastrowid
    cursor.execute("INSERT INTO staff (email, password, name, role_id, created_at, updated_at) VALUES ('return@test.com', 'password', 'Return Staff', %s, NOW(), NOW())", (role_id,))
    staff_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
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

def test_return_list_access(client, logged_in_staff_return):
    """測試退貨申請列表"""
    with patch('app.blueprints.staff.permission.require_permission', return_value=lambda f: f):
        response = client.get('/staff/return/list')
        assert response.status_code == 200
        assert "退貨管理" in response.get_data(as_text=True)

def test_return_approve(client, logged_in_staff_return):
    """測試退貨核准功能"""
    # 建立測試環境
    conn = get_db_connection()
    cursor = conn.cursor()
    # 建立一個測試會員
    cursor.execute("INSERT INTO customer (email, password, name, is_active, created_at, updated_at) VALUES ('c@t.com', 'pw', 'Test Customer', 1, NOW(), NOW())")
    c_id = cursor.lastrowid
    # 建立一個測試訂單
    cursor.execute("INSERT INTO orders (customer_id, status, total, created_at, updated_at) VALUES (%s, 'completed', 100, NOW(), NOW())", (c_id,))
    o_id = cursor.lastrowid
    # 建立測試退貨申請
    cursor.execute("INSERT INTO return_request (order_id, status, created_at, updated_at) VALUES (%s, 'pending', NOW(), NOW())", (o_id,))
    rr_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    with patch('app.blueprints.staff.permission.require_permission', return_value=lambda f: f):
        response = client.post(f'/staff/return/approve/{rr_id}', follow_redirects=True)
    
    assert response.status_code == 200
    assert "已核准" in response.get_data(as_text=True)

    # 清理資料
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM return_request WHERE id = %s", (rr_id,))
    cursor.execute("DELETE FROM orders WHERE id = %s", (o_id,))
    cursor.execute("DELETE FROM customer WHERE id = %s", (c_id,))
    conn.commit()
    cursor.close()
    conn.close()
