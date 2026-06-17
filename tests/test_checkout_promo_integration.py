import pytest
from app import create_app
from app.db import get_db_connection
from app.blueprints.home.checkout import calculate_order_totals, get_eligible_public_promos
from datetime import datetime, timedelta

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# 1. Logic Test: Order Total Calculations
def test_calculate_order_totals_logic():
    # Test Free Shipping
    subtotal = 1000
    shipping_fee = 100
    promo = {'min_order_amount': 500, 'discount_type': 'free_shipping', 'discount_value': 0}
    
    sub_disc, ship_disc, final_ship = calculate_order_totals(subtotal, shipping_fee, promo)
    assert ship_disc == 100
    assert final_ship == 0
    
    # Test Partial Shipping Deduction
    promo = {'min_order_amount': 500, 'discount_type': 'shipping_deduction', 'discount_value': 50}
    sub_disc, ship_disc, final_ship = calculate_order_totals(subtotal, shipping_fee, promo)
    assert ship_disc == 50
    assert final_ship == 50

# 2. DB/Integration Test: Eligible Promo Filtering
def test_get_eligible_public_promos():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Setup dummy user and promo
    cursor.execute("INSERT INTO promo_code (code, is_public, is_active, is_deleted, min_order_amount, usage_limit, used_count) VALUES ('PUB1', 1, 1, 0, 500, 10, 0)")
    promo_id = cursor.lastrowid
    conn.commit()
    
    promos = get_eligible_public_promos(conn, 1, 600)
    assert any(p['code'] == 'PUB1' for p in promos)
    
    # Cleanup
    cursor.execute("DELETE FROM promo_code WHERE id = %s", (promo_id,))
    conn.commit()
    cursor.close()
    conn.close()
