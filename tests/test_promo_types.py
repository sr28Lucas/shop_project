import pytest
from app.db import get_db_connection
from datetime import datetime, timedelta

@pytest.fixture
def promo_factory(auth_staff):
    """建立折扣碼的工廠"""
    def _create_promo(code, discount_type, discount_value, min_order=0):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now()
        start = now - timedelta(days=1)
        end = now + timedelta(days=1)
        
        cursor.execute("""
            INSERT INTO promo_code (code, discount_type, discount_value, min_order_amount, start_at, end_at, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s)
        """, (code, discount_type, discount_value, min_order, start, end, now, now))
        conn.commit()
        cursor.close()
        conn.close()
    return _create_promo

def test_promo_types(client, auth_client, test_product, promo_factory):
    """測試不同類型的折扣碼"""
    # 1. 建立測試使用者並登入
    auth_client.login_customer()
    
    # 2. 建立各種折扣碼
    promo_factory('PERC10', 'subtotal_discount', 10) # 10% off
    promo_factory('FIXED100', 'subtotal_deduction', 100) # 100 off
    promo_factory('SHIPFREE', 'free_shipping', 0) # Free shipping
    
    # 3. 加入商品到購物車
    client.post('/checkout/add_to_cart', data={'sku_id': test_product['sku_id'], 'qty': 1})
    
    # 檢查購物車 (假設商品價格 1000)
    # 此處邏輯需簡化：直接測試計算結果或確認折扣碼應用流程
    
    # 測試流程 (此處需依實際 checkout 邏輯調整，以下為概念模擬)
    # response = client.post('/checkout/information', data={
    #     'promo_code': 'PERC10',
    #     ...
    # })
    # 檢查 session 是否正確包含 promo_code 以及計算是否正確
    pass
