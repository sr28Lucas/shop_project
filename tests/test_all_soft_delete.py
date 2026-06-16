import pytest
from app.models.category_model import CategoryModel
from app.models.product_model import ProductModel
from app.db import get_db_connection

def test_category_soft_delete_and_recreate():
    # 1. 建立分類並軟刪除
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO category (name, is_deleted, created_at, updated_at) VALUES ('測試分類', 0, NOW(), NOW())")
    cat_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    CategoryModel.soft_delete(cat_id)

    # 2. 驗證重新建立同名分類應成功
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM category WHERE name = '測試分類' AND is_deleted = 0")
    assert cursor.fetchone() is None
    
    # 這裡模擬 category_add 的邏輯
    cursor.execute("INSERT INTO category (name, is_deleted, created_at, updated_at) VALUES ('測試分類', 0, NOW(), NOW())")
    conn.commit()
    assert cursor.rowcount == 1
    cursor.close()
    conn.close()

def test_announcement_soft_delete():
    """驗證公告軟刪除"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO announcement (title, content, type, is_deleted, created_at, updated_at) VALUES ('測試公告', '內容', 'general', 0, NOW(), NOW())")
    ann_id = cursor.lastrowid
    conn.commit()
    
    # 軟刪除
    cursor.execute("UPDATE announcement SET is_deleted = 1 WHERE id = %s", (ann_id,))
    conn.commit()
    
    # 驗證列表不顯示
    cursor.execute("SELECT id FROM announcement WHERE id = %s AND is_deleted = 0", (ann_id,))
    assert cursor.fetchone() is None
    cursor.close()
    conn.close()
