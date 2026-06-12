import pytest
from app.blueprints.home.checkout import calculate_order_totals

def test_calculate_order_totals_subtotal_discount():
    """驗證小計百分比折扣 (10% off)"""
    # promo: 10% off
    promo = {'discount_type': 'subtotal_discount', 'discount_value': 10, 'min_order_amount': 0}
    # subtotal 1000, shipping 100
    sub_disc, ship_disc, final_ship = calculate_order_totals(1000, 100, promo)
    
    assert sub_disc == 100 # 1000 * 0.1
    assert ship_disc == 0
    assert final_ship == 100

def test_calculate_order_totals_subtotal_deduction():
    """驗證固定金額折扣 (200 off)"""
    promo = {'discount_type': 'subtotal_deduction', 'discount_value': 200, 'min_order_amount': 0}
    sub_disc, ship_disc, final_ship = calculate_order_totals(1000, 100, promo)
    
    assert sub_disc == 200
    assert ship_disc == 0
    assert final_ship == 100

def test_calculate_order_totals_shipping_deduction():
    """驗證運費折抵 (50 off shipping)"""
    promo = {'discount_type': 'shipping_deduction', 'discount_value': 50, 'min_order_amount': 0}
    sub_disc, ship_disc, final_ship = calculate_order_totals(1000, 100, promo)
    
    assert sub_disc == 0
    assert ship_disc == 50
    assert final_ship == 50 # 100 - 50

def test_calculate_order_totals_free_shipping():
    """驗證免運費"""
    promo = {'discount_type': 'free_shipping', 'discount_value': 0, 'min_order_amount': 0}
    sub_disc, ship_disc, final_ship = calculate_order_totals(1000, 100, promo)
    
    assert sub_disc == 0
    assert ship_disc == 100
    assert final_ship == 0
