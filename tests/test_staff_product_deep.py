import pytest
from app.db import get_db_connection
from unittest.mock import patch

@pytest.fixture
def logged_in_staff(client):
    """模擬登入具備 'product' 權限的管理員"""
    with client.session_transaction() as sess:
        sess['staff_id'] = 1 
    return {'staff_id': 1}

@pytest.fixture
def test_category():
    """建立測試分類"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES ('測試分類', NOW(), NOW())")
    cat_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    yield cat_id

    # 清理資料
    conn = get_db_connection()
    cursor = conn.cursor()
    # 先清理關聯的產品
    cursor.execute("DELETE FROM product WHERE category_id = %s", (cat_id,))
    cursor.execute("DELETE FROM category WHERE id = %s", (cat_id,))
    conn.commit()
    cursor.close()
    conn.close()

def test_product_add_full_flow(client, logged_in_staff, test_category):
    """測試商品新增完整流程 (三層驗證)"""
    # 1. 操作驗證
    with patch('app.blueprints.staff.permission.require_permission', return_value=lambda f: f):
        response = client.post('/staff/product/add', data={
            'name': '整合測試商品',
            'category_id': test_category,
            'description': '這是完整流程測試'
        }, follow_redirects=True)
    assert response.status_code == 200
    assert "OK" in response.get_data(as_text=True)

    # 2. 資料持久化驗證
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM product WHERE name = '整合測試商品' AND is_deleted = 0")
    product = cursor.fetchone()
    assert product is not None
    assert product['category_id'] == test_category
    cursor.close()
    conn.close()

    # 3. 前端 UI 渲染驗證
    with patch('app.blueprints.staff.permission.require_permission', return_value=lambda f: f):
        response = client.get('/staff/product/list')
    assert response.status_code == 200
    assert "整合測試商品" in response.get_data(as_text=True)
