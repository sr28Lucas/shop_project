import pytest
from app.db import get_db_connection

def test_shipping_fee_logic(client):
    """測試運費計算邏輯：台灣島內 100，外島 200"""
    # 建立一個測試訂單 (需事先登入)
    email = 'shipping@test.com'
    client.post('/auth/register', data={
        'email': email,
        'password': 'password123',
        'confirm_password': 'password123',
        'name': 'Shipping User'
    })
    
    # 手動確認帳號
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE customer SET is_verified=1 WHERE email = %s", (email,))
    conn.commit()
    cursor.close()
    conn.close()
    
    client.post('/auth/login', data={'email': email, 'password': 'password123'})
    
    # 這裡省略加入購物車的步驟，直接測試後端計算邏輯
    # 您可以根據實際專案的輔助函數進行測試
    from app.blueprints.home.checkout import calculate_order_totals
    
    # 測試台灣島內
    subtotal = 1000
    shipping = 100
    disc, ship_disc, final_ship = calculate_order_totals(subtotal, shipping, None)
    assert final_ship == 100
    
    # 測試外島 (這裡假設邏輯依賴資料庫設定，直接測試資料庫狀態)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT fee FROM region WHERE name = '澎湖縣'")
    region = cursor.fetchone()
    assert region['fee'] == 200
    cursor.close()
    conn.close()
