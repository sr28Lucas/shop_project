import pytest
import re
from app import create_app
from app.db import get_db_connection
from app.utils.validators import Validator
from app.extensions import bcrypt
from datetime import datetime

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
    cursor = db_conn.cursor(dictionary=True, buffered=True)
    # 1. Cleanup old test data
    cursor.execute("SELECT id FROM product WHERE name = 'Sort Test Product'")
    old_product = cursor.fetchone()
    if old_product:
        pid = old_product['id']
        cursor.execute("DELETE FROM cart_item WHERE sku_id IN (SELECT id FROM sku WHERE variant_id IN (SELECT id FROM variant WHERE product_id = %s))", (pid,))
        cursor.execute("DELETE FROM sku WHERE variant_id IN (SELECT id FROM variant WHERE product_id = %s)", (pid,))
        cursor.execute("DELETE FROM variant WHERE product_id = %s", (pid,))
        cursor.execute("DELETE FROM product WHERE id = %s", (pid,))

    # 2. Create product
    cursor.execute("INSERT INTO product (name, category_id, is_active, created_at, updated_at) VALUES ('Sort Test Product', 1, 1, NOW(), NOW())")
    product_id = cursor.lastrowid
    db_conn.commit()
    cursor.close()
    return product_id

# 1. Validator Class Tests
def test_validator_logic():
    # Email Regex Test (Loose)
    assert Validator.is_valid_email("root@root") is True
    assert Validator.is_valid_email("a@b") is True
    assert Validator.is_valid_email("test.user@company.com") is True
    assert Validator.is_valid_email("invalid-email") is False
    assert Validator.is_valid_email("@@@") is False
    assert Validator.is_valid_email("a@") is False
    
    # Password Test (Min 4)
    assert Validator.is_valid_password("root") is True
    assert Validator.is_valid_password("123") is False
    
    # Length Guard Test
    assert Validator.is_valid_length("A" * 100, 100) is True
    assert Validator.is_valid_length("A" * 101, 100) is False
    assert Validator.is_valid_length("", 100, 1) is False
    
    # Number Guard Test
    assert Validator.is_valid_number(999999999, 999999999) is True
    assert Validator.is_valid_number(1000000000, 999999999) is False
    assert Validator.is_valid_number(-1, 999999999) is False
    assert Validator.is_valid_number("abc", 100) is False

# 2. Integration Tests (Simulating Requests)

def test_announcement_length_guard(client, db_conn):
    # Log in as staff first (need a valid staff account)
    # This assumes root@root exists or we create one
    hashed_pw = bcrypt.generate_password_hash("root").decode('utf-8')
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM staff WHERE email = 'validator_test@root'")
    cursor.execute("""
        INSERT INTO staff (email, password, name, role_id, is_active, created_at, updated_at)
        VALUES ('validator_test@root', %s, 'Tester', 1, 1, NOW(), NOW())
    """, (hashed_pw,))
    db_conn.commit()
    
    client.post('/auth/staff_login', data={'email': 'validator_test@root', 'password': 'root'})
    
    # Try to post a very long title
    long_title = "T" * 101
    response = client.post('/staff/page/announcement/add', data={
        'title': long_title,
        'content': 'Test content',
        'type': 'info'
    }, follow_redirects=True)
    assert "公告標題長度需在 1-100 字元之間" in response.data.decode('utf-8')

def test_product_boundary_guard(client, db_conn):
    pid = setup_test_data(db_conn) # Get a valid product ID
    client.post('/auth/staff_login', data={'email': 'validator_test@root', 'password': 'root'})
    
    # Try to add a variant with 1 billion price
    response = client.post(f'/staff/product/{pid}/variant/add', data={
        'color': 'Red',
        'sku_code[]': ['SKU-HUGE'],
        'size[]': ['XL'],
        'price[]': ['1000000000'], # 1B
        'cost[]': ['100'],
        'stock[]': ['10'],
        'variant_is_active': 'on'
    }, follow_redirects=True)
    assert "價格/成本上限 9.9億" in response.data.decode('utf-8')

def test_logistics_negative_guard(client, db_conn):
    client.post('/auth/staff_login', data={'email': 'validator_test@root', 'password': 'root'})
    
    # Try to set negative shipping fee
    response = client.post('/staff/order/logistics_settings', data={
        'fee_台北市': '-10'
    }, follow_redirects=True)
    assert "必須在 0 到 10,000 之間" in response.data.decode('utf-8')

def test_member_password_guard(client, db_conn):
    # Create a member
    hashed_pw = bcrypt.generate_password_hash("password123").decode('utf-8')
    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM customer WHERE email = 'member@test.com'")
    cursor.execute("""
        INSERT INTO customer (email, password, name, phone, is_active, created_at, updated_at)
        VALUES ('member@test.com', %s, 'Member', '0912345678', 1, NOW(), NOW())
    """, (hashed_pw,))
    db_conn.commit()
    
    client.post('/auth/login', data={'email': 'member@test.com', 'password': 'password123'})
    
    # Try to change password to 3 chars
    response = client.post('/customer/profile/password', data={
        'old_password': 'password123',
        'new_password': '123',
        'confirm_password': '123'
    }, follow_redirects=True)
    assert "新密碼長度至少需 4 位" in response.data.decode('utf-8')
