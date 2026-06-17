import pytest
from app.db import get_db_connection
from unittest.mock import patch

@pytest.fixture
def logged_in_staff(client):
    """模擬登入具備權限的管理員"""
    with client.session_transaction() as sess:
        sess['staff_id'] = 1 
    return {'staff_id': 1}

def test_role_list_access(client, logged_in_staff):
    """測試角色列表存取"""
    with patch('app.blueprints.staff.permission.check_permission', return_value=lambda f: f):
        response = client.get('/staff/role/list')
        assert response.status_code == 200
        assert "角色管理" in response.get_data(as_text=True)

def test_role_add_success(client, logged_in_staff):
    """測試成功新增角色"""
    with patch('app.blueprints.staff.permission.check_permission', return_value=lambda f: f):
        response = client.post('/staff/role/add', data={
            'name': 'TestRole',
            'member': '1',
            'orders': '1'
        }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "角色新增成功" in response.get_data(as_text=True)

    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM role WHERE name = 'TestRole'")
    role = cursor.fetchone()
    assert role is not None
    assert role['member'] == 1
    cursor.close()
    conn.close()

def test_role_edit_success(client, logged_in_staff):
    """測試成功更新角色"""
    # 先建立一個角色
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO role (name, created_at, updated_at) VALUES ('EditRole', NOW(), NOW())")
    r_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    with patch('app.blueprints.staff.permission.check_permission', return_value=lambda f: f):
        response = client.post(f'/staff/role/edit/{r_id}', data={
            'name': 'UpdatedRole',
            'product': '1'
        }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "角色更新成功" in response.get_data(as_text=True)

def test_role_delete_success(client, logged_in_staff):
    """測試成功刪除角色"""
    # 先建立一個角色
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO role (name, created_at, updated_at) VALUES ('DeleteRole', NOW(), NOW())")
    r_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    with patch('app.blueprints.staff.permission.check_permission', return_value=lambda f: f):
        response = client.post(f'/staff/role/delete/{r_id}', follow_redirects=True)
    
    assert response.status_code == 200
    assert "角色刪除成功" in response.get_data(as_text=True)
