import pytest
from app.db import get_db_connection
from flask import session

@pytest.fixture
def logged_in_customer(client):
    """註冊並登入一個測試會員"""
    email = 'order_user@test.com'
    password = 'password'
    client.post('/auth/register', data={
        'email': email,
        'password': password,
        'confirm_password': password,
        'name': 'Order User'
    }, follow_redirects=True)
    client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)
    return email, password

def test_order_list_access(client, logged_in_customer):
    """測試訂單列表頁面"""
    response = client.get('/customer/order/list', follow_redirects=True)
    assert response.status_code == 200
    # 根據之前的錯誤資訊，驗證頁面存在且為會員中心相關內容
    assert "會員中心" in response.get_data(as_text=True)

def test_order_view_unauthorized(client):
    """測試未登入存取訂單詳情"""
    response = client.get('/customer/order/view/1', follow_redirects=True)
    assert response.status_code == 200
    assert "登入" in response.get_data(as_text=True)

def test_order_view_not_found(client, logged_in_customer):
    """測試存取不存在的訂單"""
    response = client.get('/customer/order/view/99999', follow_redirects=True)
    assert response.status_code == 200
    assert "找不到該訂單" in response.get_data(as_text=True)
