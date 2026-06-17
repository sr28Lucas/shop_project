import pytest
from app.db import get_db_connection
from flask import session

def test_staff_profile_edit(client, auth_staff):
    """測試管理員更新個人資料"""
    # 確保已登入 (auth_staff fixture 應已處理，但這裡顯式處理以防萬一)
    with client.session_transaction() as sess:
        sess['staff_id'] = 1 # 假設 root 帳號 ID 為 1

    # 測試 GET
    response = client.get('/staff/profile/')
    assert response.status_code == 200
    
    # 測試 POST (更新成功)
    response = client.post('/staff/profile/', data={
        'name': 'New Staff Name',
        'phone': '0912345678'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "個人資料更新成功！" in response.get_data(as_text=True)
    
    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, phone FROM staff WHERE email = 'root@root'")
    staff = cursor.fetchone()
    assert staff['name'] == 'New Staff Name'
    assert staff['phone'] == '0912345678'
    cursor.close()
    conn.close()

def test_staff_profile_edit_invalid(client, auth_staff):
    """測試管理員更新個人資料 (名稱為空)"""
    with client.session_transaction() as sess:
        sess['staff_id'] = 1
        
    response = client.post('/staff/profile/', data={
        'name': '',
        'phone': '0912345678'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "姓名為必填" in response.get_data(as_text=True)

def test_staff_change_password_success(client, auth_staff):
    """測試管理員修改密碼成功"""
    with client.session_transaction() as sess:
        sess['staff_id'] = 1
        
    # 假設 root@root 的初始密碼為 'root'
    response = client.post('/staff/profile/password', data={
        'old_password': 'root',
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "密碼修改成功！" in response.get_data(as_text=True)

def test_staff_change_password_wrong_old(client, auth_staff):
    """測試管理員修改密碼失敗 (原密碼錯誤)"""
    with client.session_transaction() as sess:
        sess['staff_id'] = 1
        
    response = client.post('/staff/profile/password', data={
        'old_password': 'wrongpassword',
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "原密碼錯誤" in response.get_data(as_text=True)

def test_staff_change_password_mismatch(client, auth_staff):
    """測試管理員修改密碼失敗 (新密碼與確認不符)"""
    with client.session_transaction() as sess:
        sess['staff_id'] = 1
        
    response = client.post('/staff/profile/password', data={
        'old_password': 'root',
        'new_password': 'newpassword123',
        'confirm_password': 'differentpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "新密碼與確認密碼不一致" in response.get_data(as_text=True)
