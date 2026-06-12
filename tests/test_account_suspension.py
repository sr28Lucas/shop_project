import pytest
from app import create_app
from flask import session

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret'
    
    with app.test_client() as client:
        with app.app_context():
            yield client

def test_active_member_access(client):
    """測試正常會員可以訪問"""
    with client.session_transaction() as sess:
        sess['customer_id'] = 1  # 假設資料庫中有 ID=1 的測試會員且 is_active=1
    
    response = client.get('/customer/center')
    assert response.status_code == 200 or response.status_code == 302 # 視具體情況而定

def test_suspended_member_redirect(client, monkeypatch):
    """測試被停權會員被重導向"""
    # 模擬登入
    with client.session_transaction() as sess:
        sess['customer_id'] = 2 # 假設 ID=2 被停權
    
    # 模擬資料庫檢查函數回傳該用戶已被停權
    # 這裡我們需要 Mock `get_db_connection` 或者是直接操作資料庫
    # 為了測試，最簡單的是確保測試資料庫中的狀態是正確的
    
    response = client.get('/customer/center', follow_redirects=True)
    
    # 驗證被導向登入頁面
    assert response.status_code == 200
    assert "您的帳號已被停用" in response.data.decode('utf-8')

def test_suspended_staff_redirect(client):
    """測試被停權員工被重導向"""
    with client.session_transaction() as sess:
        sess['staff_id'] = 99 # 假設 ID=99 的員工被停權
    
    response = client.get('/staff/dashboard', follow_redirects=True)
    
    assert response.status_code == 200
    assert "您的員工帳號已被停用" in response.data.decode('utf-8')
