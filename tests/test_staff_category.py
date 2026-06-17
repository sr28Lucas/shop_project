import pytest
from app.db import get_db_connection

@pytest.fixture
def test_category_setup(client, auth_staff):
    """確保測試分類存在並清理舊測試資料"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES ('測試分類_Cat', NOW(), NOW())")
    cat_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    yield cat_id
    
    # 清理
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM category WHERE id = %s", (cat_id,))
    conn.commit()
    cursor.close()
    conn.close()

def test_category_list(client, auth_staff):
    """測試分類列表顯示"""
    response = client.get('/staff/category/')
    assert response.status_code == 200
    assert "分類管理" in response.get_data(as_text=True)

def test_category_add_success(client, auth_staff):
    """測試新增分類成功"""
    response = client.post('/staff/category/add', data={'name': '新分類'}, follow_redirects=True)
    assert response.status_code == 200
    assert "新分類" in response.get_data(as_text=True)

def test_category_add_duplicate(client, auth_staff, test_category_setup):
    """測試新增重複分類名稱"""
    # 嘗試新增與剛剛建立的分類同名的分類
    response = client.post('/staff/category/add', data={'name': '測試分類_Cat'}, follow_redirects=True)
    assert response.status_code == 200
    assert "此分類名稱已存在" in response.get_data(as_text=True)

def test_category_edit_success(client, auth_staff, test_category_setup):
    """測試修改分類名稱"""
    response = client.post(f'/staff/category/edit/{test_category_setup}', data={'name': '修改後分類'}, follow_redirects=True)
    assert response.status_code == 200
    assert "修改後分類" in response.get_data(as_text=True)

def test_category_delete_success(client, auth_staff):
    """測試刪除無商品的分類"""
    # 建立一個臨時分類
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES ('待刪除分類', NOW(), NOW())")
    cat_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    response = client.post(f'/staff/category/delete/{cat_id}', follow_redirects=True)
    assert response.status_code == 200
    assert "分類已刪除" in response.get_data(as_text=True)

def test_category_delete_with_product_fail(client, auth_staff, test_product):
    """測試刪除有商品的分類應失敗"""
    # 測試環境已有商品分類，test_product fixture 會建立商品與分類關聯
    cat_id = test_product['product_id'] # 這其實是錯誤的邏輯，應該要取得 category_id
    
    # 修正：先取得商品的 category_id
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT category_id FROM product WHERE id = %s", (test_product['product_id'],))
    cat_id = cursor.fetchone()['category_id']
    cursor.close()
    conn.close()
    
    response = client.post(f'/staff/category/delete/{cat_id}', follow_redirects=True)
    assert response.status_code == 200
    assert "此分類下尚有商品，無法刪除" in response.get_data(as_text=True)
