from flask import Blueprint, session, request, redirect, render_template, url_for, flash 
from app.db import get_db_connection
from datetime import datetime

checkout_bp = Blueprint('checkout', __name__)

def get_active_cart(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM cart WHERE customer_id = %s AND status = 'active'", (customer_id,))
    cart = cursor.fetchone()
    if not cart:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO cart (customer_id, status, created_at, updated_at) VALUES (%s, 'active', %s, %s)",
                       (customer_id, now, now))
        conn.commit()
        cart_id = cursor.lastrowid
    else:
        cart_id = cart['id']
    cursor.close()
    conn.close()
    return cart_id

@checkout_bp.route('/view_cart')
def view_cart():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 檢查並清理已刪除的商品
    cursor.execute("""
        SELECT ci.sku_id, p.name as product_name
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN product p ON s.product_id = p.id
        WHERE ci.cart_id = %s AND (s.is_deleted = 1 OR p.is_deleted = 1)
    """, (cart_id,))
    deleted_items = cursor.fetchall()
    
    if deleted_items:
        for item in deleted_items:
            flash(f"商品 '{item['product_name']}' 已下架或刪除，已自動從您的購物車中移除。")
            cursor.execute("DELETE FROM cart_item WHERE cart_id = %s AND sku_id = %s", (cart_id, item['sku_id']))
        conn.commit()

    # 獲取有效的購物車項目
    cursor.execute("""
        SELECT ci.qty, s.price, s.size, s.color, p.name as product_name, ci.sku_id, p.id as product_id
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN product p ON s.product_id = p.id
        WHERE ci.cart_id = %s AND s.is_deleted = 0 AND p.is_deleted = 0
    """, (cart_id,))
    cart_items = cursor.fetchall()
    
    subtotal = sum(item['qty'] * item['price'] for item in cart_items)
    
    cursor.close()
    conn.close()
    
    return render_template('home/cart.html', cart_items=cart_items, subtotal=subtotal)

@checkout_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    sku_id = request.form.get('sku_id')
    qty = int(request.form.get('qty', 1))
    
    if not sku_id:
        return "<script>alert('請選擇規格！'); window.history.back();</script>"
        
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if item exists
    cursor.execute("SELECT qty FROM cart_item WHERE cart_id = %s AND sku_id = %s", (cart_id, sku_id))
    item = cursor.fetchone()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if item:
        cursor.execute("UPDATE cart_item SET qty = qty + %s, updated_at = %s WHERE cart_id = %s AND sku_id = %s",
                       (qty, now, cart_id, sku_id))
    else:
        cursor.execute("INSERT INTO cart_item (cart_id, sku_id, qty, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
                       (cart_id, sku_id, qty, now, now))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('home.checkout.view_cart'))

@checkout_bp.route('/update_qty', methods=['POST'])
def update_qty():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    sku_id = request.form['sku_id']
    qty = request.form['qty']
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE cart_item SET qty = %s, updated_at = %s WHERE cart_id = %s AND sku_id = %s",
                   (qty, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cart_id, sku_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('home.checkout.view_cart'))

@checkout_bp.route('/remove_item', methods=['POST'])
def remove_item():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    sku_id = request.form['sku_id']
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cart_item WHERE cart_id = %s AND sku_id = %s", (cart_id, sku_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('home.checkout.view_cart'))

@checkout_bp.route('information', methods=['POST'])
def information():
    return "結帳資訊頁面 (待實作)"

@checkout_bp.route('payment')
def payment():
    pass

@checkout_bp.route('place_order')
def place_order():
    pass

@checkout_bp.route('complete')
def complete():
    pass


