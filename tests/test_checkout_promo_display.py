import pytest
from app import create_app
from app.db import get_db_connection
from datetime import datetime, timedelta

@pytest.fixture
def client():
    app = create_app({'TESTING': True, 'DATABASE': 'test_db.sql'})
    with app.test_client() as client:
        yield client

def test_eligible_promo_display(client):
    # Setup: Create a public promo code
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    start_at = now - timedelta(days=1)
    end_at = now + timedelta(days=1)
    
    cursor.execute("""
        INSERT INTO promo_code (code, description, discount_type, discount_value, is_public, start_at, end_at, is_active, is_deleted)
        VALUES ('TESTPROMO', 'Test Description', 'subtotal_discount', 10, 1, %s, %s, 1, 0)
    """, (start_at, end_at))
    promo_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    
    # Act: Go to checkout information page (Assuming user is logged in and has items in cart)
    # This requires mocking auth and cart. 
    # For now, this is a conceptual test structure.
    
    # response = client.get('/checkout/information')
    # assert b'TESTPROMO' in response.data
    # assert b'Test Description' in response.data
    
    # Cleanup: Delete the promo
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM promo_code WHERE id = %s", (promo_id,))
    conn.commit()
    cursor.close()
    conn.close()
