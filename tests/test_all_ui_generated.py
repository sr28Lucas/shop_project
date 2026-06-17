import pytest
from flask import url_for

# 自動產生的測試檔案，針對所有 HTML 模板進行基礎驗證
# 此檔案由代理程式自動產生。

class TestAllUI:
    # 這裡將定義各模板對應的測試案例
    
    def test_auth_login(self, client):
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert b"<title>" in response.data

    def test_auth_register(self, client):
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert b"<title>" in response.data

    # TODO: 繼續補全其他模板測試...
    # 若某模板無對應明確路由，請在 docs/test_coverage_matrix.md 註記
