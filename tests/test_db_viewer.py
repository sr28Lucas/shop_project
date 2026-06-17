import pytest
from app.db import get_db_connection

# 測試時模擬 root 角色 (注意：這裡的測試需要一個擁有 root 角色的 staff)
@pytest.fixture
def auth_root(client):
    """登入 root 管理員"""
    client.post('/auth/staff_login', data={'email': 'root@root', 'password': 'root'})
    return {'email': 'root@root'}

def test_db_list_access(client, auth_root):
    """測試 DB Viewer 列表存取"""
    response = client.get('/staff/db_viewer/list')
    assert response.status_code == 200
    assert "請選擇資料表" in response.get_data(as_text=True)
    # 至少應該有 staff 表
    assert "staff" in response.get_data(as_text=True)

def test_db_view_table(client, auth_root):
    """測試瀏覽特定資料表"""
    response = client.get('/staff/db_viewer/view/staff')
    assert response.status_code == 200
    assert "staff" in response.get_data(as_text=True)
    assert "email" in response.get_data(as_text=True)

def test_db_view_search(client, auth_root):
    """測試資料表搜尋功能"""
    response = client.get('/staff/db_viewer/view/staff?search=root')
    assert response.status_code == 200
    # 搜尋結果中應包含 root 帳號的 email
    assert "root@root" in response.get_data(as_text=True)
