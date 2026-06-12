import pytest
from app import create_app
from app.db import get_db_connection
from app.extensions import bcrypt
from datetime import datetime, timedelta
import re

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test_secret_key"
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db_conn():
    conn = get_db_connection()
    yield conn
    conn.close()

def setup_test_data(db_conn):
    cursor = db_conn.cursor(dictionary=True)
    # 1. Cleanup old test data
    cursor.execute("SELECT id FROM product WHERE name = 'Sort Test Product'")
    old_product = cursor.fetchone()
    if old_product:
        pid = old_product['id']
        cursor.execute("DELETE FROM cart_item WHERE sku_id IN (SELECT id FROM sku WHERE variant_id IN (SELECT id FROM variant WHERE product_id = %s))", (pid,))
        cursor.execute("DELETE FROM sku WHERE variant_id IN (SELECT id FROM variant WHERE product_id = %s)", (pid,))
        cursor.execute("DELETE FROM variant WHERE product_id = %s", (pid,))
        cursor.execute("DELETE FROM product WHERE id = %s", (pid,))

    # 2. Create a deactivated member
    hashed_pw = bcrypt.generate_password_hash("password123").decode('utf-8')
    cursor.execute("DELETE FROM customer WHERE email = 'deactivated@test.com'")
    cursor.execute("""
        INSERT INTO customer (email, password, name, phone, is_active, created_at, updated_at)
        VALUES ('deactivated@test.com', %s, 'Deactivated User', '0912345678', 0, NOW(), NOW())
    """, (hashed_pw,))
    
    # 3. Create a deactivated staff
    cursor.execute("DELETE FROM staff WHERE email = 'deactivated_staff@test.com'")
    cursor.execute("""
        INSERT INTO staff (email, password, name, role_id, is_active, created_at, updated_at)
        VALUES ('deactivated_staff@test.com', %s, 'Deactivated Staff', 1, 0, NOW(), NOW())
    """, (hashed_pw,))
    
    # 4. Create product with unsorted sizes
    cursor.execute("INSERT INTO product (name, category_id, is_active, created_at, updated_at) VALUES ('Sort Test Product', 1, 1, NOW(), NOW())")
    product_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO variant (product_id, color, is_active, created_at, updated_at) VALUES (%s, 'Blue', 1, NOW(), NOW())", (product_id,))
    variant_id = cursor.lastrowid
    
    # Insert sizes out of order: L, S, M, XL, XS
    sizes = [('L', 100), ('S', 100), ('M', 100), ('XL', 100), ('XS', 100)]
    for size, price in sizes:
        cursor.execute("INSERT INTO sku (variant_id, sku_code, size, price, stock, is_active, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, 1, NOW(), NOW())",
                       (variant_id, f"SKU-{size}-{product_id}", size, price, 10))
    
    db_conn.commit()
    cursor.close()
    return product_id

# Bug 8: Account deactivation ineffective
def test_deactivated_login(client, db_conn):
    setup_test_data(db_conn)
    # Member login
    response = client.post('/auth/login', data={
        'email': 'deactivated@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert "您的帳號已被停用" in response.data.decode('utf-8')
    
    # Staff login
    response = client.post('/auth/staff_login', data={
        'email': 'deactivated_staff@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    assert "員工帳號已被停用" in response.data.decode('utf-8')

# Bug 2: Product sizes not sorted
def test_product_size_sorting(client, db_conn):
    product_id = setup_test_data(db_conn)
    response = client.get(f'/product/{product_id}')
    assert response.status_code == 200
    
    content = response.data.decode('utf-8')
    # In the template, skus are passed to the frontend or rendered in some way.
    # We implemented the sorting in product_view() which passes them to the template.
    # Let's check the HTML for the order of sizes.
    # Looking at the original product_view.html, it uses variantsData = [... {skus: [...]}]
    skus_match = re.search(r'skus: \[\s*(.*?)\s*\]', content, re.DOTALL)
    if skus_match:
        skus_content = skus_match.group(1)
        sizes_found = re.findall(r"size: '(.*?)'", skus_content)
        # Expected order: XS, S, M, L, XL
        assert sizes_found == ['XS', 'S', 'M', 'L', 'XL']

# Bug 3 & 1: Negative prices and overflow
from app.blueprints.home.checkout import calculate_order_totals
def test_calculate_order_totals_logic():
    # Negative price test (discount > subtotal)
    promo = {'discount_type': 'subtotal_deduction', 'discount_value': 200, 'min_order_amount': 0}
    subtotal_discount, shipping_discount, final_shipping_fee = calculate_order_totals(100, 60, promo)
    assert subtotal_discount == 100 # Capped at subtotal
    assert final_shipping_fee == 60
    
    # Percentage discount test
    promo = {'discount_type': 'subtotal_discount', 'discount_value': 50, 'min_order_amount': 0}
    subtotal_discount, shipping_discount, final_shipping_fee = calculate_order_totals(100, 60, promo)
    assert subtotal_discount == 50
    
    # Shipping discount test
    promo = {'discount_type': 'shipping_deduction', 'discount_value': 100, 'min_order_amount': 0}
    subtotal_discount, shipping_discount, final_shipping_fee = calculate_order_totals(100, 60, promo)
    assert shipping_discount == 60 # Capped at original shipping
    assert final_shipping_fee == 0

# Bug 4: Credit card validation
from app.utils.validators import Validator
def test_credit_card_validation():
    assert Validator.is_valid_credit_card("1234567890123456") is True
    assert Validator.is_valid_credit_card("1234-5678-9012-3456") is True
    assert Validator.is_valid_credit_card("1234 5678 9012 3456") is True
    assert Validator.is_valid_credit_card("123456789012345") is False # 15 digits
    assert Validator.is_valid_credit_card("12345678901234567") is False # 17 digits
    assert Validator.is_valid_credit_card("-1234567890123456") is False # negative
    assert Validator.is_valid_credit_card("abcdefghijklmnop") is False

# Bug 6: Discount code range
from app.blueprints.staff.promo import validate_discount
def test_promo_validation():
    assert validate_discount('subtotal_discount', 110) == "小計打折 (百分比) 必須介於 0 到 100 之間"
    assert validate_discount('subtotal_discount', -5) == "小計打折 (百分比) 必須介於 0 到 100 之間"
    assert validate_discount('subtotal_deduction', -10) == "折抵金額不能為負數"
    assert validate_discount('shipping_deduction', -10) == "折抵金額不能為負數"
    assert validate_discount('subtotal_discount', 50) is None
    assert validate_discount('subtotal_deduction', 500) is None

# Bug 1: Quantity overflow
def test_quantity_limit(client, db_conn):
    product_id = setup_test_data(db_conn)
    cursor = db_conn.cursor(dictionary=True, buffered=True)
    cursor.execute("SELECT id FROM sku WHERE variant_id IN (SELECT id FROM variant WHERE product_id = %s)", (product_id,))
    sku = cursor.fetchone()
    
    # Login first
    hashed_pw = bcrypt.generate_password_hash("password123").decode('utf-8')
    cursor.execute("DELETE FROM customer WHERE email = 'tester@test.com'")
    cursor.execute("INSERT INTO customer (email, password, name, phone, is_active, created_at, updated_at) VALUES ('tester@test.com', %s, 'Tester', '0911', 1, NOW(), NOW())", (hashed_pw,))
    db_conn.commit()
    
    client.post('/auth/login', data={'email': 'tester@test.com', 'password': 'password123'})
    
    # Try to add 1000 items
    response = client.post('/checkout/add_to_cart', data={
        'sku_id': sku['id'],
        'qty': 1000
    })
    assert response.status_code == 400
    data = response.get_json()
    assert "單次加入數量不能超過 999" in data['message']
