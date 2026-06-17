import pytest
from app.db import get_db_connection
from datetime import datetime

def setup_order(client, test_product, status='completed'):
    # Login as buyer
    email = f'buyer_{datetime.now().timestamp()}@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Buyer'})
    client.post('/auth/login', data={'email': email, 'password': 'password'})
    
    # Add to cart
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    
    # Place order
    client.post('/checkout/information', data={
        'selected_skus': [str(test_product['sku_id'])],
        'name': '收件人', 'phone': '0912345678', 'region': '臺北市', 'locality': '中正區', 'address': '測試地址 123 號'
    }, follow_redirects=True)
    client.post('/checkout/payment', data={'card_number': '1234567812345678'}, follow_redirects=True)
    client.post('/checkout/place_order', follow_redirects=True)
    
    # Update status
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM orders ORDER BY id DESC LIMIT 1")
    order = cursor.fetchone()
    cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order['id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    return order['id']

from unittest.mock import patch

@pytest.fixture
def auth_statistic_staff(client):
    """登入具備統計權限的員工"""
    # 建立一個擁有統計權限的角色
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO role (name, statistic, created_at, updated_at) VALUES ('StatRole', 1, NOW(), NOW())")
    role_id = cursor.lastrowid
    cursor.execute("INSERT INTO staff (email, password, name, role_id, created_at, updated_at) VALUES ('stat@test.com', 'password', 'Stat Staff', %s, NOW(), NOW())", (role_id,))
    staff_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    with client.session_transaction() as sess:
        sess['staff_id'] = staff_id
        
    yield {'staff_id': staff_id}
    
    # 清理
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM staff WHERE id = %s", (staff_id,))
    cursor.execute("DELETE FROM role WHERE id = %s", (role_id,))
    conn.commit()
    cursor.close()
    conn.close()

def test_statistic_revenue_access(client, auth_statistic_staff):
    """測試營收統計頁面存取"""
    with patch('app.blueprints.staff.permission.check_permission', return_value=True):
        response = client.get('/staff/statistic/revenue')
    assert response.status_code == 200
    assert "營收" in response.get_data(as_text=True)

def test_statistic_sales_access(client, auth_statistic_staff):
    """測試銷售統計頁面存取"""
    with patch('app.blueprints.staff.permission.check_permission', return_value=True):
        response = client.get('/staff/statistic/sales')
    assert response.status_code == 200
    assert "銷售" in response.get_data(as_text=True)

def test_statistic_hot_items_access(client, auth_statistic_staff):
    """測試潛力爆款統計頁面存取"""
    with patch('app.blueprints.staff.permission.check_permission', return_value=True):
        response = client.get('/staff/statistic/hot-items')
    assert response.status_code == 200
    assert "潛力爆款" in response.get_data(as_text=True)

def test_statistic_calculations(client, auth_statistic_staff, test_product):
    """測試營收統計頁面顯示數據是否正確"""
    
    # 建立一個已完成訂單 (假設金額為 1000)
    setup_order(client, test_product, status='completed')
    
    # 建立一個待出貨訂單
    setup_order(client, test_product, status='pending')
    
    # 建立一個已退款訂單
    setup_order(client, test_product, status='refunded')
    
    # 查詢統計
    with patch('app.blueprints.staff.permission.check_permission', return_value=True):
        response = client.get('/staff/statistic/revenue')
    assert response.status_code == 200
    
    content = response.get_data(as_text=True)
    
    # 驗證統計值
    assert "總營收" in content
    assert "1000" in content or "1,000" in content
    assert "有效訂單數" in content
    assert ">1</div>" in content 
    
    assert "待出貨訂單" in content
    assert ">1</div>" in content
    
    assert "已退款訂單" in content
    assert ">1</div>" in content

def test_return_deduction_in_statistics(client, auth_statistic_staff):
    """驗證退貨會正確從營收統計中扣除"""
    
    # 1. 建立獨立的測試環境
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 建立唯一分類
    cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES (%s, %s, %s)", (f"TestCat_{datetime.now().timestamp()}", now, now))
    cat_id = cursor.lastrowid
    
    # 建立商品
    cursor.execute("INSERT INTO product (category_id, name, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)", 
                   (cat_id, f'TestProd_{datetime.now().timestamp()}', 1, now, now))
    p_id = cursor.lastrowid
    
    # 建立變體與SKU
    cursor.execute("INSERT INTO variant (product_id, color, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)", (p_id, 'Color', 1, now, now))
    v_id = cursor.lastrowid
    cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                   (v_id, 'SKU', 'M', 1000, 500, 10, 1, now, now))
    sku_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    test_product = {'sku_id': sku_id, 'product_id': p_id}
    
    # 2. 建立訂單並完成
    order_id = setup_order(client, test_product, status='completed')
    
    # 3. 執行退貨流程
    conn = get_db_connection()
    cursor = conn.cursor()
    # 取得 order_item_id
    cursor.execute("SELECT id FROM order_item WHERE order_id = %s", (order_id,))
    order_item_id = cursor.fetchone()[0]
    
    # 建立退貨請求
    cursor.execute("INSERT INTO return_request (order_id, status, requested_at) VALUES (%s, 'refunded', NOW())", (order_id,))
    return_request_id = cursor.lastrowid
    cursor.execute("INSERT INTO return_item (return_request_id, order_item_id, qty) VALUES (%s, %s, 1)", (return_request_id, order_item_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    # 4. 查詢統計，預期該分類營收應為 0
    today = datetime.now().strftime('%Y-%m-%d')
    with patch('app.blueprints.staff.permission.check_permission', return_value=True):
        response = client.get(f'/staff/statistic/revenue?start_date={today}&end_date={today}')
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    
    # 驗證該分類營收為 0
    assert "$0.00" in content
