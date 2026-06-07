import pytest
from io import BytesIO
from unittest.mock import patch
from app.db import get_db_connection

def test_add_product_with_multiple_images(client, auth_staff):
    """測試同時新增商品與多張圖片"""
    
    # 準備 POST 資料 (文字欄位 + 模擬圖片)
    data = {
        'name': '整合測試商品',
        'category_id': '1', # 假設分類 ID 1 存在
        'description': '測試描述',
        'is_active': 'on',
        'images': [
            (BytesIO(b'img1'), 'img1.jpg'),
            (BytesIO(b'img2'), 'img2.jpg')
        ]
    }
    
    with patch('werkzeug.datastructures.FileStorage.save'), \
         patch('os.path.exists', return_value=True), \
         patch('os.makedirs'):
        
        response = client.post(
            '/staff/product/add', 
            data=data, 
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
    assert response.status_code == 200
    
    # 驗證資料庫：商品與圖片皆新增
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM product WHERE name = '整合測試商品'")
    product = cursor.fetchone()
    assert product is not None
    
    cursor.execute("SELECT count(*) as count FROM image WHERE product_id = %s", (product['id'],))
    image_count = cursor.fetchone()['count']
    assert image_count == 2
    
    cursor.close()
    conn.close()

def test_add_variant_with_image(client, auth_staff, test_product):
    """測試同時新增變體與專屬圖片"""
    
    product_id = test_product['product_id']
    
    # 準備 POST 資料
    data = {
        'color': '紅色',
        'variant_is_active': 'on',
        'sku_code[]': ['SKU-RED-TEST'],
        'size[]': ['M'],
        'price[]': ['500'],
        'cost[]': ['200'],
        'stock[]': ['10'],
        'is_active[]': ['1'],
        'variant_image': (BytesIO(b'variant img'), 'variant.jpg')
    }
    
    with patch('werkzeug.datastructures.FileStorage.save'), \
         patch('os.path.exists', return_value=True), \
         patch('os.makedirs'):
        
        response = client.post(
            f'/staff/product/{product_id}/variant/add',
            data=data,
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
    assert response.status_code == 200
    
    # 驗證資料庫：變體與圖片皆新增
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM variant WHERE product_id = %s AND color = '紅色'", (product_id,))
    variant = cursor.fetchone()
    assert variant is not None
    
    cursor.execute("SELECT count(*) as count FROM image WHERE variant_id = %s", (variant['id'],))
    image_count = cursor.fetchone()['count']
    assert image_count == 1
    
    cursor.close()
    conn.close()
