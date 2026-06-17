import pytest
from app.db import get_db_connection
from datetime import datetime

# 測試輔助：建立一個測試帳號並自訂狀態
def create_test_customer(email, is_verified=1, is_active=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    # 簡單的密碼：password (bcrypt hash)
    password = b'$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p3S8/4S3/n23a.z1.M/8QYfO'
    cursor.execute("""
        INSERT INTO customer (email, password, name, is_verified, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """, (email, password, 'Test User', is_verified, is_active))
    conn.commit()
    cursor.close()
    conn.close()

def test_login_unverified_account(client):
    """測試登入尚未驗證信箱的帳號"""
    create_test_customer('unverified@test.com', is_verified=0)
    
    response = client.post('/auth/login', data={
        'email': 'unverified@test.com',
        'password': 'password'
    }, follow_redirects=True)
    
    assert "尚未完成信箱驗證" in response.get_data(as_text=True)

def test_login_inactive_account(client):
    """測試登入被停權的帳號"""
    create_test_customer('inactive@test.com', is_verified=1, is_active=0)
    
    response = client.post('/auth/login', data={
        'email': 'inactive@test.com',
        'password': 'password'
    }, follow_redirects=True)
    
    assert "帳號已被停用" in response.get_data(as_text=True)

def test_forgot_password_nonexistent_email(client):
    """測試忘記密碼功能 (Email 不存在)"""
    # 依據程式碼，應提示通用的發送成功訊息
    response = client.post('/auth/forgot_password', data={
        'email': 'notexist@test.com'
    }, follow_redirects=True)
    
    assert "若此 Email 有註冊，重設連結已發送" in response.get_data(as_text=True)
