import pytest
from bs4 import BeautifulSoup

# Define routes and expected main container classes for structural validation
PAGE_STRUCTURE_CHECKS = [
    ('/', 'max-w-7xl'),
    ('/hot_items', 'max-w-7xl'),
    ('/announcements', 'max-w-4xl'),
]

@pytest.mark.parametrize("route, expected_class", PAGE_STRUCTURE_CHECKS)
def test_page_structure(client, route, expected_class):
    """驗證關鍵頁面是否包含預期的結構容器"""
    response = client.get(route)
    assert response.status_code == 200
    
    soup = BeautifulSoup(response.data, 'html.parser')
    assert soup.find(class_=expected_class) is not None, f"頁面 {route} 缺少容器類別: {expected_class}"

def test_base_navigation_elements(client):
    """驗證所有頁面基礎導覽列的一致性"""
    response = client.get('/')
    soup = BeautifulSoup(response.data, 'html.parser')
    
    # 確保導覽列存在 (搜尋使用 Tailwind，舊 nav class 應改為驗證新的標籤結構)
    nav = soup.find('nav', class_='hidden') # md:flex class
    assert nav is not None
