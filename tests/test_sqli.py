import pytest

# SQL Injection 攻擊向量列表
SQLI_PAYLOADS = [
    "' OR '1'='1",
    "admin' --",
    "1'; DROP TABLE users; --",
    "' UNION SELECT null, null, null --",
]

def test_sql_injection_login(client):
    """測試登入功能的 SQL Injection 防禦"""
    for payload in SQLI_PAYLOADS:
        response = client.post('/auth/login', data={
            'email': payload,
            'password': 'password'
        }, follow_redirects=True)
        # 不應跳轉到會員中心
        assert response.status_code == 200
        assert '/customer/center' not in response.request.path

def test_sql_injection_product_search(client):
    """測試商品搜尋功能的 SQL Injection 防禦"""
    for payload in SQLI_PAYLOADS:
        # 使用正確的 URL
        response = client.get(f'/?q={payload}')
        assert response.status_code == 200
        # 應正常顯示頁面，不應拋出 Internal Server Error (500)
        assert "500 Internal Server Error" not in response.get_data(as_text=True)

def test_sql_injection_staff_order_search(client, auth_staff):
    """測試後台訂單搜尋功能的 SQL Injection 防禦"""
    for payload in SQLI_PAYLOADS:
        response = client.get(f'/staff/order/list?search={payload}')
        assert response.status_code == 200
        assert "500 Internal Server Error" not in response.get_data(as_text=True)
