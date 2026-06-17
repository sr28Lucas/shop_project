import pytest
from app.db import get_db_connection

def test_dashboard_ui_layout(client, auth_staff):
    """測試後台儀錶板基礎 UI 元素是否存在"""
    response = client.get('/staff/dashboard')
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    
    # 驗證必要元素
    assert "VIVID<span>Admin</span>" in content
    assert "儀錶板" in content
    assert "商品管理" in content
    assert "訂單管理" in content
    assert "iframe" in content

def test_sidebar_links_render(client, auth_staff):
    """測試選單連結是否正確渲染 (驗證權限過濾)"""
    response = client.get('/staff/dashboard')
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    
    # 確保有權限顯示的選單連結存在
    # 假設 root 帳號擁有所有權限
    assert 'href="/staff/product/list"' in content or 'data-title="產品管理"' in content
    assert 'href="/staff/order/list"' in content or 'data-title="出貨管理"' in content
    assert 'href="/staff/staff_account/list"' in content or 'data-title="員工帳號管理"' in content

def test_dashboard_iframe_mechanism(client, auth_staff):
    """測試儀錶板 JS 機制 (簡化版：驗證 JS 腳本存在)"""
    response = client.get('/staff/dashboard')
    content = response.get_data(as_text=True)
    
    # 檢查是否含有處理 iframe 的 JS
    assert "function toggleSidebar()" in content
    assert "document.getElementById(\"contentFrame\")" in content
