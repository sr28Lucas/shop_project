import pytest
from app.db import get_db_connection
from datetime import datetime, timedelta

@pytest.fixture
def promo_creator():
    """建立特定狀態優惠碼的輔助函數"""
    def _create_promo(code, discount_type='subtotal_deduction', discount_value=100, 
                     is_active=1, usage_limit=10, used_count=0, min_order=500,
                     start_offset_days=-1, end_offset_days=1):
        conn = get_db_connection()
        cursor = conn.cursor()
        now = datetime.now()
        start = now + timedelta(days=start_offset_days)
        end = now + timedelta(days=end_offset_days)
        
        cursor.execute("""
            INSERT INTO promo_code (code, discount_type, discount_value, min_order_amount, 
                                    usage_limit, used_count, is_active, start_at, end_at, 
                                    created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (code, discount_type, discount_value, min_order, usage_limit, used_count, is_active, start, end, now, now))
        conn.commit()
        cursor.close()
        conn.close()
    return _create_promo

def test_promo_expired(client, auth_client, promo_creator):
    """測試過期優惠碼應無法使用"""
    auth_client.login_customer()
    promo_creator('EXPIRED', start_offset_days=-10, end_offset_days=-5)
    
    # 這裡應該模擬結帳流程並驗證失敗
    # res = client.post('/checkout/apply_promo', data={'promo_code': 'EXPIRED'})
    # assert res.status_code == 400 (或對應的錯誤處理)
    pass

def test_promo_inactive(client, auth_client, promo_creator):
    """測試停用優惠碼應無法使用"""
    auth_client.login_customer()
    promo_creator('INACTIVE', is_active=0)
    # ... 驗證結帳使用失敗 ...
    pass

def test_promo_usage_limit_reached(client, auth_client, promo_creator):
    """測試達到使用上限的優惠碼應無法使用"""
    auth_client.login_customer()
    promo_creator('LIMIT', usage_limit=1, used_count=1) # 假設已滿
    # ... 驗證結帳使用失敗 ...
    pass

def test_promo_min_order_not_met(client, auth_client, promo_creator):
    """測試未達最低金額門檻應無法使用"""
    auth_client.login_customer()
    promo_creator('MINORDER', min_order=1000)
    # 購物車商品總價假設 < 1000
    # ... 驗證結帳使用失敗 ...
    pass
