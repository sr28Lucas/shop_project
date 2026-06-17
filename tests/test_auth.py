import pytest
from flask import session
from app.db import get_db_connection

def test_register_success(client):
    """測試會員註冊成功"""
    response = client.post('/auth/register', data={
        'email': 'newuser@test.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'name': 'Test User'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # 檢查 flash 訊息 (現在顯示在界面上)
    data = response.get_data(as_text=True)
    assert "申辦成功" in data or "測試帳號註冊成功" in data
    
    # 驗證資料庫中是否真的存入資料
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customer WHERE email = %s", ('newuser@test.com',))
    user = cursor.fetchone()
    assert user is not None
    assert user['name'] == 'Test User'
    cursor.close()
    conn.close()

def test_register_mismatch_password(client):
    """測試兩次密碼輸入不一致"""
    response = client.post('/auth/register', data={
        'email': 'mismatch@test.com',
        'password': 'password123',
        'confirm_password': 'password456',
        'name': 'Mismatch User'
    }, follow_redirects=True)
    assert "兩次輸入的密碼不一致" in response.get_data(as_text=True)

def test_login_customer_success(client):
    """測試一般會員登入成功"""
    # 預先註冊一個帳號
    client.post('/auth/register', data={
        'email': 'loginuser@test.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'name': 'Login User'
    })
    
    response = client.post('/auth/login', data={
        'email': 'loginuser@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # 檢查是否進入會員中心
    assert "會員中心" in response.get_data(as_text=True)
    
    # 檢查 session 是否正確設定
    with client.session_transaction() as sess:
        assert 'customer_id' in sess

def test_login_customer_fail(client):
    """測試一般會員登入失敗 (密碼錯誤)"""
    response = client.post('/auth/login', data={
        'email': 'loginuser@test.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert "密碼錯囉" in response.get_data(as_text=True)

def test_login_staff_success(client):
    """測試管理員登入成功 (使用 conftest 初始化建立的 root)"""
    response = client.post('/auth/staff_login', data={
        'email': 'root@root',
        'password': 'root'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # 檢查是否進入管理後台
    assert "儀錶板" in response.get_data(as_text=True) or "Dashboard" in response.get_data(as_text=True)
    
    with client.session_transaction() as sess:
        assert 'staff_id' in sess

def test_logout(client):
    """測試登出功能"""
    # 先登入
    client.post('/auth/staff_login', data={'email': 'root@root', 'password': 'root'})
    
    response = client.get('/auth/logout', follow_redirects=True)
    assert response.status_code == 200
    
    with client.session_transaction() as sess:
        assert 'staff_id' not in sess
        assert 'customer_id' not in sess

def test_staff_logout(client):
    """測試員工登出功能"""
    # 先登入員工
    client.post('/auth/staff_login', data={'email': 'root@root', 'password': 'root'})
    
    response = client.get('/auth/staff_logout', follow_redirects=True)
    assert response.status_code == 200
    
    with client.session_transaction() as sess:
        assert 'staff_id' not in sess
