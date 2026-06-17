import pytest
from app.db import get_db_connection
from datetime import datetime

@pytest.fixture
def test_role():
    """建立一個測試角色"""
    conn = get_db_connection()
    cursor = conn.cursor()
    unique_name = f'測試角色_{datetime.now().timestamp()}'
    cursor.execute("INSERT INTO role (name, created_at, updated_at) VALUES (%s, NOW(), NOW())", (unique_name,))
    role_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return role_id

def test_staff_list_access(client, auth_staff):
    """測試員工列表存取"""
    response = client.get('/staff/staff_account/list')
    assert response.status_code == 200
    assert "員工帳號管理" in response.get_data(as_text=True)

def test_staff_add_success(client, auth_staff, test_role):
    """測試新增員工成功"""
    response = client.post('/staff/staff_account/add', data={
        'name': '新員工',
        'email': f'new_staff_{datetime.now().timestamp()}@test.com',
        'phone': '0912345678',
        'role_id': test_role,
        'password': 'password123',
        'password_confirm': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "員工帳號新增成功" in response.get_data(as_text=True)

def test_staff_add_validation(client, auth_staff, test_role):
    """測試新增員工欄位驗證"""
    # 測試密碼不一致
    response = client.post('/staff/staff_account/add', data={
        'name': '新員工',
        'email': 'valid@test.com',
        'phone': '0912345678',
        'role_id': test_role,
        'password': 'pass',
        'password_confirm': 'different'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "密碼與確認密碼不一致" in response.get_data(as_text=True)

def test_staff_edit_success(client, auth_staff, test_role):
    """測試編輯員工資訊成功"""
    # 先建立一個員工
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO staff (name, email, phone, role_id, password, created_at, updated_at) VALUES ('待編輯', 'edit@test.com', '0912345678', %s, 'hashed', NOW(), NOW())", (test_role,))
    staff_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    # 執行編輯
    response = client.post(f'/staff/staff_account/edit/{staff_id}', data={
        'name': '已修改',
        'phone': '0987654321',
        'role_id': test_role,
        'is_active': 'on'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "員工帳號更新成功" in response.get_data(as_text=True)

def test_staff_edit_root_protection(client, auth_staff):
    """測試 Root 帳號無法編輯"""
    # 找到 root 帳號的 id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM staff WHERE email = 'root@root'")
    root_id = cursor.fetchone()['id']
    cursor.close()
    conn.close()
    
    response = client.post(f'/staff/staff_account/edit/{root_id}', data={
        'name': '駭客修改',
        'phone': '0900000000',
        'role_id': 1
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "Root 帳號資料受保護" in response.get_data(as_text=True)
