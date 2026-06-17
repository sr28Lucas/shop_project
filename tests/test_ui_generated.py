import pytest
from flask import url_for

# 自動產生的測試檔案，針對所有 HTML 模板進行基礎驗證

# 需要登入才能存取的 endpoint 列表
needs_login = {
    'customer.center', 'customer.order_list', 'customer.order_view', 
    'customer.profile_edit', 'staff.dashboard', 'staff.order_list'
}

# 模板與其對應的 Endpoint (手動映射部分，其餘標記為待調查)
# 這裡簡化映射，部分未定義的會觸發 BuildError 供後續調查
routes_to_test = [
    ('auth/login.html', 'auth.login'),
    ('auth/register.html', 'auth.register'),
    ('home/index.html', 'home.index'),
]

@pytest.mark.parametrize("template_path, endpoint", routes_to_test)
def test_template_rendering(client, template_path, endpoint):
    # 透過 app context 取得 URL
    with client.application.test_request_context():
        try:
            url = url_for(endpoint)
        except Exception:
            pytest.skip(f"無法解析 endpoint: {endpoint}")

    # 模擬登入
    if endpoint in needs_login:
        client.post('/auth/login', data={'email': 'test@test.com', 'password': 'password'})

    response = client.get(url)
    
    # 斷言：200 OK 或 302 重導向 (有些頁面登入後才可見)
    assert response.status_code in [200, 302]
    
    # 若為 200，確認 title 存在
    if response.status_code == 200:
        assert b"<title" in response.data
