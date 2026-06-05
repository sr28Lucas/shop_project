import pytest
from flask import url_for

def test_root_has_all_access(client):
    """驗證 Root 帳號具備完整權限"""
    client.post('/auth/staff_login', data={'email': 'root@root', 'password': 'root'})
    
    # 測試各個模組
    assert client.get('/staff/product/list').status_code == 200
    assert client.get('/staff/order/list').status_code == 200
    assert client.get('/staff/member/list').status_code == 200
    assert client.get('/staff/promo/list').status_code == 200

def test_product_manager_isolation(client, staff_factory):
    """驗證商品管理員只能管理商品，無法管理訂單或會員"""
    pm = staff_factory("ProductManager", permissions={'product': 1})
    client.post('/auth/staff_login', data={'email': pm['email'], 'password': pm['password']})
    
    # 應可進入商品列表
    assert client.get('/staff/product/list').status_code == 200
    
    # 應無法進入訂單列表 (重導向回 dashboard 並閃現錯誤)
    response = client.get('/staff/order/list', follow_redirects=True)
    assert "您沒有權限執行此操作" in response.get_data(as_text=True)
    assert "/staff/dashboard" in response.request.path

def test_order_manager_isolation(client, staff_factory):
    """驗證訂單管理員只能管理訂單"""
    om = staff_factory("OrderManager", permissions={'orders': 1})
    client.post('/auth/staff_login', data={'email': om['email'], 'password': om['password']})
    
    assert client.get('/staff/order/list').status_code == 200
    
    # 無法進入商品列表
    response = client.get('/staff/product/list', follow_redirects=True)
    assert "您沒有權限執行此操作" in response.get_data(as_text=True)

def test_restricted_manager_access(client, staff_factory):
    """驗證無權限管理員無法進入任何模組"""
    rm = staff_factory("Restricted", permissions={}) # 全 0
    client.post('/auth/staff_login', data={'email': rm['email'], 'password': rm['password']})
    
    modules = ['/staff/product/list', '/staff/order/list', '/staff/member/list', '/staff/promo/list']
    for module in modules:
        response = client.get(module, follow_redirects=True)
        assert "您沒有權限執行此操作" in response.get_data(as_text=True)

def test_unauthorized_redirect(client):
    """驗證未登入人員存取後台會被導向登入頁"""
    # 清除 session
    client.get('/auth/staff_logout')
    
    response = client.get('/staff/dashboard', follow_redirects=True)
    # 由於 staff 模組的 login_required 通常是檢查 session，沒登入會導向 login
    assert "/auth/staff_login" in response.request.path
