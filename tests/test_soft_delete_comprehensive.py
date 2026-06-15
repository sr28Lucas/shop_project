import pytest
from app.models.category_model import CategoryModel
from app.models.product_model import ProductModel
from app.db import get_db_connection

# 💡 此測試檔案旨在驗證軟刪除在複雜情境下的表現
# 確保歷史紀錄不受影響，但現在的操作會自動過濾。

def test_soft_delete_cart_interaction(client, auth_client):
    """驗證軟刪除商品後，購物車邏輯應自動處理"""
    # 登入並加入商品
    auth_client.login_customer()
    
    # 建立商品
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO product (name, is_active, is_deleted, created_at, updated_at) VALUES ('暫存商品', 1, 0, NOW(), NOW())")
    prod_id = cursor.lastrowid
    cursor.execute("INSERT INTO variant (product_id, color, is_active, created_at, updated_at) VALUES (%s, '藍', 1, NOW(), NOW())", (prod_id,))
    var_id = cursor.lastrowid
    cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, created_at, updated_at) VALUES (%s, 'SKU-TEMP', 'M', 100, 50, 10, 1, NOW(), NOW())", (var_id,))
    sku_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    # 加入購物車
    client.post('/checkout/add_to_cart', data={'sku_id': sku_id, 'qty': 1})
    
    # 執行軟刪除
    ProductModel.soft_delete(prod_id)
    
    # 檢視購物車，應觸發自動清理機制
    response = client.get('/checkout/view_cart', follow_redirects=True)
    assert response.status_code == 200
    
    # 直接驗證資料庫中購物車項目是否已被移除
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM cart_item WHERE sku_id = %s", (sku_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    assert count == 0

def test_historical_data_integrity():
    """驗證軟刪除商品後，歷史統計不應受到影響"""
    # 模擬歷史銷售
    conn = get_db_connection()
    cursor = conn.cursor()
    # 建立一個已售出的商品
    cursor.execute("INSERT INTO product (name, is_active, is_deleted, created_at, updated_at) VALUES ('歷史商品', 1, 0, NOW(), NOW())")
    prod_id = cursor.lastrowid
    cursor.execute("INSERT INTO orders (customer_id, subtotal, total, name, phone, region, locality, address, created_at, updated_at) VALUES (1, 100, 100, '名', '0900000000', '地區', '鄉鎮', '地址', NOW(), NOW())")
    order_id = cursor.lastrowid
    cursor.execute("INSERT INTO order_item (order_id, product_id, product_name, variant_name, sku_code, qty, original_price, unit_price, unit_cost) VALUES (%s, %s, '歷史商品', '變體', 'CODE', 1, 100, 100, 50)", (order_id, prod_id))
    conn.commit()
    
    # 執行軟刪除
    ProductModel.soft_delete(prod_id)
    
    # 統計歷史銷售不應受影響
    cursor.execute("SELECT COUNT(*) as count FROM order_item WHERE product_id = %s", (prod_id,))
    assert cursor.fetchone()[0] == 1
    cursor.close()
    conn.close()
