import pytest
from app.db import get_db_connection
from unittest.mock import patch

@pytest.fixture
def logged_in_staff(client):
    """模擬登入具備權限的管理員"""
    with client.session_transaction() as sess:
        sess['staff_id'] = 1 
    return {'staff_id': 1}

def test_member_list_access(client, logged_in_staff):
    """測試會員列表存取與篩選"""
    with patch('app.blueprints.staff.member.require_permission', return_value=lambda f: f):
        response = client.get('/staff/member/list')
        assert response.status_code == 200
        assert "會員瀏覽" in response.get_data(as_text=True)

        # 測試篩選
        response = client.get('/staff/member/list?status=active')
        assert response.status_code == 200

def test_member_detail_access(client, logged_in_staff):
    """測試會員詳細資訊存取"""
    # 先建立一個測試會員
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO customer (email, password, name, is_active, created_at, updated_at) VALUES ('m@t.com', 'pw', 'Test Member', 1, NOW(), NOW())")
    m_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    with patch('app.blueprints.staff.member.require_permission', return_value=lambda f: f):
        response = client.get(f'/staff/member/detail/{m_id}')
        assert response.status_code == 200
        assert "Test Member" in response.get_data(as_text=True)

def test_member_toggle_status(client, logged_in_staff):
    """測試切換會員狀態"""
    # 建立一個測試會員
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO customer (email, password, name, is_active, created_at, updated_at) VALUES ('m2@t.com', 'pw', 'Toggle User', 1, NOW(), NOW())")
    m_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    with patch('app.blueprints.staff.member.require_permission', return_value=lambda f: f):
        response = client.post(f'/staff/member/toggle/{m_id}', follow_redirects=True)
        assert response.status_code == 200
        assert "已停用" in response.get_data(as_text=True)

    # 驗證狀態 - 重新建立連線以確保穩定
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT is_active FROM customer WHERE id = %s", (m_id,))
    res = cursor.fetchone()
    assert res is not None and res['is_active'] == 0
    cursor.close()
    conn.close()
