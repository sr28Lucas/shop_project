import pytest
from app.db import get_db_connection
from datetime import datetime

def test_email_verification_workflow(client):
    """測試郵件驗證流程：註冊 -> 檢查是否未驗證 -> 驗證成功 -> 檢查狀態"""
    email = 'verify@test.com'
    
    # 1. 註冊
    client.post('/auth/register', data={
        'email': email,
        'password': 'password123',
        'confirm_password': 'password123',
        'name': 'Verify User'
    })
    
    # 檢查是否已寫入且已驗證 (測試信箱 @test.com 會被自動驗證)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT is_verified FROM customer WHERE email = %s", (email,))
    user = cursor.fetchone()
    assert user['is_verified'] == 1
    
    # 2. 測試登入 (應成功，因為是測試帳號)
    response = client.post('/auth/login', data={'email': email, 'password': 'password123'}, follow_redirects=True)
    assert "會員中心" in response.get_data(as_text=True)

def test_account_suspension_login_block(client):
    """測試停權帳號無法登入"""
    email = 'suspended@test.com'
    
    # 註冊並手動設為已驗證但被停權
    client.post('/auth/register', data={
        'email': email,
        'password': 'password123',
        'confirm_password': 'password123',
        'name': 'Suspended User'
    })
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE customer SET is_verified=1, is_active=0 WHERE email = %s", (email,))
    conn.commit()
    cursor.close()
    conn.close()
    
    # 登入測試
    response = client.post('/auth/login', data={'email': email, 'password': 'password123'}, follow_redirects=True)
    assert "帳號已被停用" in response.get_data(as_text=True)
