import pytest
from app.db import get_db_connection

@pytest.fixture
def test_product_for_variant(client, auth_staff):
    """建立測試商品供變體測試"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM category LIMIT 1")
    cat_id = cursor.fetchone()['id']
    
    # 建立商品
    cursor.execute("INSERT INTO product (category_id, name, is_active, created_at, updated_at) VALUES (%s, %s, 1, NOW(), NOW())", 
                   (cat_id, 'Variant Test Product',))
    p_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return p_id

def test_variant_add_success(client, auth_staff, test_product_for_variant):
    """測試成功新增變體與多個 SKU"""
    response = client.post(f'/staff/product/{test_product_for_variant}/variant/add', data={
        'color': '紅色',
        'variant_is_active': '1',
        'sku_code[]': ['RED-S', 'RED-M'],
        'size[]': ['S', 'M'],
        'price[]': ['100', '110'],
        'cost[]': ['50', '55'],
        'stock[]': ['10', '20'],
        'is_active[]': ['0', '1']
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "新增變體與規格成功" in response.get_data(as_text=True)

def test_variant_add_duplicate_sku(client, auth_staff, test_product_for_variant):
    """測試在同一表單中提交重複的 SKU Code"""
    response = client.post(f'/staff/product/{test_product_for_variant}/variant/add', data={
        'color': '藍色',
        'sku_code[]': ['BLUE-S', 'BLUE-S'], # 重複
        'size[]': ['S', 'M'],
        'price[]': ['100', '100'],
        'cost[]': ['50', '50'],
        'stock[]': ['10', '10']
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "新增失敗：表單中包含重複的貨號" in response.get_data(as_text=True)

def test_variant_add_negative_values(client, auth_staff, test_product_for_variant):
    """測試提交負數值"""
    response = client.post(f'/staff/product/{test_product_for_variant}/variant/add', data={
        'color': '綠色',
        'sku_code[]': ['GREEN-S'],
        'size[]': ['S'],
        'price[]': ['-10'], # 負數
        'cost[]': ['50'],
        'stock[]': ['10']
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "新增失敗：價格/成本上限 9.9億，庫存上限 100萬，且不能為負數！" in response.get_data(as_text=True)
def test_variant_edit_duplicate_sku_database(client, auth_staff, test_product_for_variant):
    """測試修改變體時，新增的 SKU 與資料庫中已有的 SKU 重複"""
    # 1. 先新增一個變體
    client.post(f'/staff/product/{test_product_for_variant}/variant/add', data={
        'color': '黃色',
        'sku_code[]': ['YELLOW-M'],
        'size[]': ['M'],
        'price[]': ['100'],
        'cost[]': ['50'],
        'stock[]': ['10']
    }, follow_redirects=True)
    
    # 2. 獲取剛剛新增的變體 ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM variant WHERE product_id = %s AND color = '黃色'", (test_product_for_variant,))
    v_id = cursor.fetchone()['id']
    cursor.close()
    conn.close()
    
    # 3. 再新增一個變體，並使用與上面相同的 SKU Code
    response = client.post(f'/staff/product/{test_product_for_variant}/variant/add', data={
        'color': '金色',
        'sku_code[]': ['YELLOW-M'], # 重複
        'size[]': ['M'],
        'price[]': ['100'],
        'cost[]': ['50'],
        'stock[]': ['10']
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "新增失敗：貨號 &#39;YELLOW-M&#39; 已經存在且正在使用中" in response.get_data(as_text=True)
