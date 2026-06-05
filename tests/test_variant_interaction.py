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

def test_variant_full_lifecycle_interaction(client, auth_staff, test_product_for_variant):
    """模擬完整的前端互動：新增變體 -> 編輯移除 SKU -> 驗證刪除"""
    product_id = test_product_for_variant
    
    # 1. 新增變體 (包含兩個 SKU)
    client.post(f'/staff/product/{product_id}/variant/add', data={
        'color': '互動測試色',
        'variant_is_active': '1',
        'sku_code[]': ['INT-1', 'INT-2'],
        'size[]': ['S', 'M'],
        'price[]': ['100', '200'],
        'cost[]': ['50', '100'],
        'stock[]': ['10', '20'],
        'is_active[]': ['0', '1']
    }, follow_redirects=True)
    
    # 獲取變體 ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM variant WHERE product_id = %s AND color = '互動測試色'", (product_id,))
    v_id = cursor.fetchone()['id']
    
    # 獲取兩個 SKU 的 ID
    cursor.execute("SELECT id, sku_code FROM sku WHERE variant_id = %s", (v_id,))
    skus = cursor.fetchall()
    sku_id_1 = next(s['id'] for s in skus if s['sku_code'] == 'INT-1')
    sku_id_2 = next(s['id'] for s in skus if s['sku_code'] == 'INT-2')
    cursor.close()
    conn.close()
    
    # 2. 編輯變體：只保留 SKU INT-2，移除 INT-1
    # 模擬表單只送出 INT-2 的資料
    client.post(f'/staff/product/{product_id}/variant/{v_id}/edit', data={
        'color': '互動測試色',
        'variant_is_active': '1',
        'sku_id[]': [str(sku_id_2)],
        'sku_code[]': ['INT-2'],
        'size[]': ['M'],
        'price[]': ['200'],
        'cost[]': ['100'],
        'stock[]': ['20'],
        'is_active[]': ['0']
    }, follow_redirects=True)
    
    # 3. 驗證 INT-1 被軟刪除 (is_active = 0)，INT-2 仍然存在 (is_active = 1)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT is_active FROM sku WHERE id = %s", (sku_id_1,))
    assert cursor.fetchone()['is_active'] == 0
    
    cursor.execute("SELECT is_active FROM sku WHERE id = %s", (sku_id_2,))
    assert cursor.fetchone()['is_active'] == 1 # 根據程式邏輯，未啟用的 SKU 仍為 active 但狀態不同，或者這裡我們測試邏輯
    
    cursor.close()
    conn.close()

def test_variant_add_then_delete_all_skus(client, auth_staff, test_product_for_variant):
    """測試新增變體後，將所有 SKU 移除的極端情況"""
    product_id = test_product_for_variant
    
    # 1. 新增
    client.post(f'/staff/product/{product_id}/variant/add', data={
        'color': '刪除測試色',
        'sku_code[]': ['DEL-1'],
        'size[]': ['S'],
        'price[]': ['100'],
        'cost[]': ['50'],
        'stock[]': ['10'],
        'is_active[]': ['0']
    }, follow_redirects=True)
    
    # 2. 獲取變體 ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM variant WHERE product_id = %s AND color = '刪除測試色'", (product_id,))
    v_id = cursor.fetchone()['id']
    cursor.close()
    conn.close()
    
    # 3. 編輯：不送出任何 SKU 資料
    client.post(f'/staff/product/{product_id}/variant/{v_id}/edit', data={
        'color': '刪除測試色',
        'variant_is_active': '1'
    }, follow_redirects=True)
    
    # 4. 驗證所有 SKU 皆被軟刪除
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT count(*) as cnt FROM sku WHERE variant_id = %s AND is_active != 0", (v_id,))
    assert cursor.fetchone()['cnt'] == 0
    cursor.close()
    conn.close()
