import pytest
from app.db import get_db_connection

def test_cart_update_invalid_item(client, auth_client):
    """測試更新購物車中不存在的商品"""
    # 假設這是一個不存在的 sku_id
    response = client.post('/checkout/update_qty', data={
        'sku_id': '99999',
        'qty': 1
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # 理論上系統應該要處理或至少不應該刪除其他正確資料
    # 這裡驗證它不會導致不可預期的錯誤

def test_cart_remove_invalid_item(client, auth_client):
    """測試移除購物車中不存在的商品"""
    response = client.post('/checkout/remove_item', data={
        'sku_id': '99999'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # 確保不會導致應用程式崩潰

def test_cart_update_invalid_qty(client, auth_client, test_product):
    """測試更新無效的數量 (負數)"""
    # 使用 auth_client 確保已登入 (正確方法: login_customer)
    email = 'stability_test@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Stability User'})
    auth_client.login_customer(email=email, password='password')
    
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    
    # 檢查是否確實有項目
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # 需要限定為該使用者的購物車
    cursor.execute("""
        SELECT ci.qty FROM cart_item ci
        JOIN cart c ON ci.cart_id = c.id
        JOIN customer cu ON c.customer_id = cu.id
        WHERE ci.sku_id = %s AND cu.email = %s
    """, (test_product['sku_id'], email))
    before_item = cursor.fetchone()
    assert before_item is not None, "Before update: item not found"
    
    response = client.post('/checkout/update_qty', data={
        'sku_id': test_product['sku_id'],
        'qty': -5
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # 驗證數量沒有被更新成負數，且商品還在
    cursor.execute("""
        SELECT ci.qty FROM cart_item ci
        JOIN cart c ON ci.cart_id = c.id
        JOIN customer cu ON c.customer_id = cu.id
        WHERE ci.sku_id = %s AND cu.email = %s
    """, (test_product['sku_id'], email))
    after_item = cursor.fetchone()
    assert after_item is not None, "After update: item not found"
    assert after_item['qty'] > 0
    cursor.close()
    conn.close()
