import pytest
from app.db import get_db_connection
from datetime import datetime

@pytest.fixture
def promo_data(db_setup):
    """建立測試優惠碼"""
    conn = get_db_connection()
    cursor = conn.cursor()
    code = f'TEST{datetime.now().timestamp()}'
    cursor.execute("""
        INSERT INTO promo_code (code, description, discount_type, discount_value, usage_limit, min_order_amount, start_at, end_at, created_at, updated_at)
        VALUES (%s, '測試優惠', 'subtotal_discount', 10, 10, 0, %s, %s, %s, %s)
    """, (code, datetime(2026,1,1), datetime(2026,12,31), datetime.now(), datetime.now()))
    conn.commit()
    cursor.close()
    conn.close()
    return code

def test_promo_add(client, auth_staff, promo_data):
    """測試新增優惠碼"""
    # 這裡主要是測試列表與新增功能
    response = client.get('/staff/promo/list')
    assert response.status_code == 200
    assert promo_data in response.get_data(as_text=True)

def test_role_list(client, auth_staff):
    """測試角色列表"""
    response = client.get('/staff/role/list')
    assert response.status_code == 200
    assert "root" in response.get_data(as_text=True)
