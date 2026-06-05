import pytest

def test_rbac_restriction(client, staff_factory):
    """測試員工權限限制：無權限者不可存取特定頁面"""
    # 建立一個「僅有訂單管理權限」的員工
    staff_data = staff_factory('OrderManager', {'orders': 1})
    
    # 登入
    client.post('/auth/staff_login', data={'email': staff_data['email'], 'password': staff_data['password']})
    
    # 嘗試存取「員工帳號管理」頁面 (應被拒絕)
    response = client.get('/staff/staff/list', follow_redirects=True)
    
    # 斷言權限不足 (通常會導向首頁或回傳 403)
    # 此處假設 403 或其他拒絕形式，需視實際程式邏輯而定
    assert response.status_code != 200
