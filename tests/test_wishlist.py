import pytest
from app.db import get_db_connection

@pytest.fixture
def auth_customer_session(client):
    """建立並登入一個測試會員，返回 Email"""
    email = f'user_{pytest.gen_unique_id()}@test.com'
    password = 'password'
    client.post('/auth/register', data={
        'email': email, 'password': password, 'confirm_password': password, 'name': 'User'
    })
    client.post('/auth/login', data={'email': email, 'password': password})
    return email

# Helper for unique IDs
pytest.gen_unique_id = lambda: __import__('datetime').datetime.now().timestamp()

def test_wishlist_toggle(client, auth_customer_session, test_product):
    """測試願望清單新增與移除"""
    # 新增
    response = client.post(f'/wishlist/toggle/{test_product["product_id"]}')
    assert response.status_code == 200
    assert response.json['action'] == 'added'
    
    # 檢查是否在清單中
    response = client.get('/wishlist/')
    assert "測試商品" in response.get_data(as_text=True)
    
    # 移除
    response = client.post(f'/wishlist/toggle/{test_product["product_id"]}')
    assert response.status_code == 200
    assert response.json['action'] == 'removed'
    
    # 檢查是否不在清單中
    response = client.get('/wishlist/')
    assert "測試商品" not in response.get_data(as_text=True)
