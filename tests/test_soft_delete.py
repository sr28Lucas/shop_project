import pytest
from app.models.category_model import CategoryModel
from app.models.product_model import ProductModel
from app.db import get_db_connection

def test_soft_delete_category():
    # 1. 新增一個分類並刪除
    conn = get_db_connection()
    cursor = conn.cursor()
    # 確保所有必要欄位都在INSERT中，移除未定義欄位
    cursor.execute("INSERT INTO category (name, is_active, is_deleted, created_at, updated_at) VALUES ('測試刪除分類', 1, 0, NOW(), NOW())")
    cat_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    # 2. 執行軟刪除
    CategoryModel.soft_delete(cat_id)

    # 3. 驗證是否無法透過 Model 取得
    category = CategoryModel.get_by_id(cat_id)
    assert category is None

    # 4. 驗證是否不在 get_all 清單中
    all_cats = CategoryModel.get_all()
    assert all_cats is not None
    assert all(c['id'] != cat_id for c in all_cats)

def test_soft_delete_product():
    # 1. 新增一個商品並刪除
    conn = get_db_connection()
    cursor = conn.cursor()
    # 這裡的INSERT需要考慮所有必填欄位 (category_id, name, description, is_active, is_deleted)
    # 假設 category_id 至少有一個存在的ID，或我們先不插 category_id (視FK約束而定)
    # 檢查 schema得知 category_id 是 nullable 的
    cursor.execute("INSERT INTO product (name, description, is_active, is_deleted, created_at, updated_at) VALUES ('測試刪除商品', 'desc', 1, 0, NOW(), NOW())")
    prod_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()

    # 2. 執行軟刪除
    ProductModel.soft_delete(prod_id)

    # 3. 驗證是否無法透過 Model 取得
    product = ProductModel.get_by_id(prod_id)
    assert product is None

    # 4. 驗證是否不在 get_all 清單中
    all_prods = ProductModel.get_all()
    assert all_prods is not None
    assert all(p['id'] != prod_id for p in all_prods)
