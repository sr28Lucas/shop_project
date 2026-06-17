import pytest
from app.db import get_db_connection
from unittest.mock import patch
from datetime import datetime

@pytest.fixture
def logged_in_staff(client):
    """模擬登入具備 'promo' 權限的管理員"""
    # 建立角色與管理員
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO role (name, promo, created_at, updated_at) VALUES ('PromoRole', 1, NOW(), NOW())")
    role_id = cursor.lastrowid
    cursor.execute("INSERT INTO staff (email, password, name, role_id, created_at, updated_at) VALUES ('promo@test.com', 'password', 'Promo Staff', %s, NOW(), NOW())", (role_id,))
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

def test_promo_list_access(client, logged_in_staff):
    """測試促銷列表存取 (三層驗證)"""
    with patch('app.blueprints.staff.permission.require_permission', return_value=lambda f: f):
        response = client.get('/staff/promo/list')
        assert response.status_code == 200
        assert "折扣碼管理" in response.get_data(as_text=True)

def test_promo_add_success(client, logged_in_staff):
    """測試成功新增促銷碼 (三層驗證)"""
    code = f'TEST{datetime.now().timestamp()}'
    
    with patch('app.blueprints.staff.permission.require_permission', return_value=lambda f: f):
        response = client.post('/staff/promo/add', data={
            'code': code,
            'description': '測試促銷',
            'discount_type': 'subtotal_discount',
            'discount_value': '10',
            'usage_limit': '100',
            'min_order_amount': '0',
            'start_at': '',
            'end_at': ''
        }, follow_redirects=True)
    
    # 1. 操作驗證
    assert response.status_code == 200
    assert "折扣碼新增成功" in response.get_data(as_text=True)
    
    # 2. 資料持久化驗證
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM promo_code WHERE code = %s AND is_deleted = 0", (code,))
    promo = cursor.fetchone()
    assert promo is not None
    assert promo['discount_value'] == 10.0
    cursor.close()
    conn.close()
    
    # 3. 前端 UI 渲染驗證
    assert code in response.get_data(as_text=True)
