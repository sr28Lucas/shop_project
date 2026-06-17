import pytest
from app.db import get_db_connection
from flask import session

def test_product_list_access(client, auth_staff):
    """測試管理員商品列表存取與篩選"""
    # 基本存取
    response = client.get('/staff/product/list')
    assert response.status_code == 200
    assert "產品管理" in response.get_data(as_text=True)

    # 測試分類篩選 (假設至少有一個分類存在)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM category LIMIT 1")
    cat = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if cat:
        response = client.get(f'/staff/product/list?category_id={cat["id"]}')
        assert response.status_code == 200

def test_bulk_update_status_success(client, auth_staff, test_product):
    """測試批次更新商品狀態"""
    prod_id = test_product['product_id']
    
    # 將狀態改為關閉 (off)
    response = client.post('/staff/product/bulk_update_status', data={
        'product_ids': [str(prod_id)],
        'action': 'off'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "已成功更新 1 個商品狀態" in response.get_data(as_text=True)
    
    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT is_active FROM product WHERE id = %s", (prod_id,))
    prod = cursor.fetchone()
    assert prod['is_active'] == 0
    cursor.close()
    conn.close()

def test_bulk_update_status_multiple_products(client, auth_staff):
    """測試批次更新多個商品狀態"""
    # 建立兩個商品
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO product (category_id, name, is_active, is_deleted, created_at, updated_at) VALUES (1, '商品1', 0, 0, NOW(), NOW())")
    prod1 = cursor.lastrowid
    cursor.execute("INSERT INTO product (category_id, name, is_active, is_deleted, created_at, updated_at) VALUES (1, '商品2', 0, 0, NOW(), NOW())")
    prod2 = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    # 批次更新為啟用 (on)
    response = client.post('/staff/product/bulk_update_status', data={
        'product_ids': [str(prod1), str(prod2)],
        'action': 'on'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "已成功更新 2 個商品狀態" in response.get_data(as_text=True)

    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT is_active FROM product WHERE id IN (%s, %s)", (prod1, prod2))
    products = cursor.fetchall()
    assert all(p['is_active'] == 1 for p in products)
    cursor.close()
    conn.close()

def test_product_add_success(client, auth_staff):
    """測試管理員新增商品"""
    # 獲取一個分類 ID
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM category LIMIT 1")
    cat = cursor.fetchone()
    cursor.close()
    conn.close()
    
    assert cat is not None, "測試資料庫中需要有分類"
    
    # 執行新增
    response = client.post('/staff/product/add', data={
        'name': '新測試商品',
        'category_id': cat['id'],
        'description': '這是測試商品的描述'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "OK" in response.get_data(as_text=True)
    
    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM product WHERE name = '新測試商品' AND is_deleted = 0")
    prod = cursor.fetchone()
    assert prod is not None
    cursor.close()
    conn.close()
