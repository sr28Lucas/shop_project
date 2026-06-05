import pytest
from app.db import get_db_connection

@pytest.fixture
def auth_staff(client):
    """登入管理員"""
    client.post('/auth/staff_login', data={'email': 'root@root', 'password': 'root'})
    return {'email': 'root@root'}

def test_staff_dashboard(client, auth_staff):
    """測試管理員儀表板存取"""
    response = client.get('/staff/dashboard')
    assert response.status_code == 200
    assert "儀錶板" in response.get_data(as_text=True)

def test_product_add_success(client, auth_staff):
    """測試管理員新增商品"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM category LIMIT 1")
    cat = cursor.fetchone()
    cat_id = cat['id']
    cursor.close()
    conn.close()
    
    response = client.post('/staff/product/add', data={
        'name': 'Staff Created Product',
        'category_id': cat_id,
        'description': 'This is a test product created by staff.'
    })
    assert response.status_code == 200
    assert "OK" in response.get_data(as_text=True)
    
    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM product WHERE name = %s", ('Staff Created Product',))
    product = cursor.fetchone()
    assert product is not None
    cursor.close()
    conn.close()

def test_product_delete(client, auth_staff, test_product):
    """測試管理員刪除商品 (軟刪除)"""
    response = client.post(f'/staff/product/delete/{test_product["product_id"]}', follow_redirects=True)
    assert response.status_code == 200
    
    # 驗證資料庫 (is_active 應變為 0)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT is_active FROM product WHERE id = %s", (test_product['product_id'],))
    product = cursor.fetchone()
    assert product['is_active'] == 0
    cursor.close()
    conn.close()

def test_order_list_access(client, auth_staff):
    """測試管理員訂單列表存取"""
    response = client.get('/staff/order/list')
    assert response.status_code == 200
    assert "訂單" in response.get_data(as_text=True)

def test_member_list_access(client, auth_staff):
    """測試管理員會員列表存取"""
    response = client.get('/staff/member/list')
    assert response.status_code == 200
    assert "會員" in response.get_data(as_text=True)
