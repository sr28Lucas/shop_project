import pytest
from app.db import get_db_connection

def test_variant_and_sku_status_and_soft_delete(client, auth_client, test_product):
    """驗證 Variant/SKU 的啟用狀態(is_active)與軟刪除(is_deleted)邏輯"""
    auth_client.login_staff()
    product_id = test_product['product_id']
    
    # 1. 取得現有 Variant 和 SKU
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM variant WHERE product_id = %s AND is_deleted = 0", (product_id,))
    variant = cursor.fetchone()
    variant_id = variant['id']
    
    cursor.execute("SELECT id FROM sku WHERE variant_id = %s AND is_deleted = 0", (variant_id,))
    sku = cursor.fetchone()
    sku_id = sku['id']
    cursor.close()
    conn.close()

    # 2. 測試軟刪除 (Delete) - 應設為 is_deleted=1 且 is_active=0
    client.post(f'/staff/product/{product_id}/variant/{variant_id}/delete', follow_redirects=True)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT is_deleted, is_active FROM variant WHERE id = %s", (variant_id,))
    v = cursor.fetchone()
    assert v['is_deleted'] == 1, "Variant should be marked as deleted"
    assert v['is_active'] == 0, "Variant should be deactivated after deletion"
    
    cursor.execute("SELECT is_deleted, is_active FROM sku WHERE id = %s", (sku_id,))
    s = cursor.fetchone()
    assert s['is_deleted'] == 1, "SKU should be marked as deleted"
    assert s['is_active'] == 0, "SKU should be deactivated after deletion"
    
    # 3. 測試 SKU 獨立刪除 (應設為 is_deleted=1, is_active=0)
    # 為了測試，先重新建立一個 SKU 關聯到同變體
    cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, is_deleted, created_at, updated_at) VALUES (%s, 'SKU-NEW', 'L', 100, 50, 5, 1, 0, NOW(), NOW())", (variant_id,))
    new_sku_id = cursor.lastrowid
    conn.commit()
    
    client.post(f'/staff/product/sku/delete/{new_sku_id}', follow_redirects=True)
    
    cursor.execute("SELECT is_deleted, is_active FROM sku WHERE id = %s", (new_sku_id,))
    s_new = cursor.fetchone()
    assert s_new['is_deleted'] == 1
    assert s_new['is_active'] == 0
    
    cursor.close()
    conn.close()
