import pytest
from app import create_app
from app.db import get_db_connection
from app.blueprints.home.checkout import calculate_order_totals, get_eligible_public_promos, validate_promo_code
from datetime import datetime, timedelta

@pytest.fixture
def conn():
    conn = get_db_connection()
    yield conn
    conn.close()

def setup_promo(conn, code, is_public, discount_type, discount_value, usage_limit=10, per_user_limit=1):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO promo_code (code, is_public, is_active, is_deleted, discount_type, discount_value, min_order_amount, usage_limit, used_count, per_user_limit)
        VALUES (%s, %s, 1, 0, %s, %s, 100, %s, 0, %s)
    """, (code, is_public, discount_type, discount_value, usage_limit, per_user_limit))
    promo_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    return promo_id

def test_all_discount_types(conn):
    subtotal = 1000
    shipping_fee = 100
    
    # 1. Subtotal Percentage Discount
    promo = {'discount_type': 'subtotal_discount', 'discount_value': 10, 'min_order_amount': 0}
    sub_disc, _, _ = calculate_order_totals(subtotal, shipping_fee, promo)
    assert sub_disc == 100 # 10% of 1000

    # 2. Subtotal Deduction
    promo = {'discount_type': 'subtotal_deduction', 'discount_value': 200, 'min_order_amount': 0}
    sub_disc, _, _ = calculate_order_totals(subtotal, shipping_fee, promo)
    assert sub_disc == 200

    # 3. Shipping Deduction
    promo = {'discount_type': 'shipping_deduction', 'discount_value': 50, 'min_order_amount': 0}
    _, ship_disc, _ = calculate_order_totals(subtotal, shipping_fee, promo)
    assert ship_disc == 50

    # 4. Free Shipping
    promo = {'discount_type': 'free_shipping', 'discount_value': 0, 'min_order_amount': 0}
    _, ship_disc, _ = calculate_order_totals(subtotal, shipping_fee, promo)
    assert ship_disc == 100

def test_public_vs_hidden_visibility(conn):
    setup_promo(conn, 'PUBLIC1', 1, 'free_shipping', 0)
    setup_promo(conn, 'HIDDEN1', 0, 'free_shipping', 0)
    
    promos = get_eligible_public_promos(conn, 1, 1000)
    codes = [p['code'] for p in promos]
    
    assert 'PUBLIC1' in codes
    assert 'HIDDEN1' not in codes

def test_usage_limits(conn):
    # Setup promo with limit 1
    promo_id = setup_promo(conn, 'LIMIT1', 1, 'free_shipping', 0, usage_limit=1, per_user_limit=1)
    
    # Validate initially valid
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM promo_code WHERE id = %s", (promo_id,))
    promo = cursor.fetchone()
    is_valid, _ = validate_promo_code(conn, promo, 1000, 1)
    assert is_valid is True
    
    # Simulate usage
    cursor.execute("UPDATE promo_code SET used_count = 1 WHERE id = %s", (promo_id,))
    conn.commit()
    
    # Validate now invalid
    cursor.execute("SELECT * FROM promo_code WHERE id = %s", (promo_id,))
    promo = cursor.fetchone()
    is_valid, err = validate_promo_code(conn, promo, 1000, 1)
    assert is_valid is False
    assert "上限" in err
    
    cursor.close()
