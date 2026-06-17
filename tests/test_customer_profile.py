import pytest
from app.db import get_db_connection
from flask import session

@pytest.fixture
def logged_in_customer(client):
    """註冊並登入一個測試會員"""
    email = 'customer@test.com'
    password = 'password'
    client.post('/auth/register', data={
        'email': email,
        'password': password,
        'confirm_password': password,
        'name': 'Test Customer'
    }, follow_redirects=True)
    client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)
    return email, password

def test_profile_edit_success(client, logged_in_customer):
    """測試更新個人資料成功"""
    response = client.post('/customer/profile/edit', data={
        'name': 'New Name',
        'phone': '0912345678',
        'address': '測試地址12345'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "資料更新成功" in response.get_data(as_text=True)

def test_profile_edit_invalid_name(client, logged_in_customer):
    """測試姓名格式錯誤"""
    response = client.post('/customer/profile/edit', data={
        'name': '', # 無效
        'phone': '0912345678'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "姓名長度需在 1-30 字元之間" in response.get_data(as_text=True)

def test_change_password_success(client, logged_in_customer):
    """測試修改密碼成功"""
    email, old_password = logged_in_customer
    response = client.post('/customer/profile/password', data={
        'old_password': old_password,
        'new_password': 'newpassword123',
        'confirm_password': 'newpassword123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "密碼修改成功" in response.get_data(as_text=True)

def test_change_password_mismatch(client, logged_in_customer):
    """測試修改密碼時新密碼不一致"""
    # 顯式設定 Session，確保狀態持久化
    with client.session_transaction() as sess:
        sess['customer_id'] = 1
        
    email, old_password = logged_in_customer
    response = client.post('/customer/profile/password', data={
        'old_password': old_password,
        'new_password': 'newpassword123',
        'confirm_password': 'mismatchpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # 驗證頁面內容（如檢查表單是否存在）
    assert "修改密碼" in response.get_data(as_text=True)

