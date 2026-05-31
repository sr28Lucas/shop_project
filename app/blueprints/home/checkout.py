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

@checkout_bp.route('/information', methods=['GET', 'POST'])
def information():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取會員資料
    cursor.execute("SELECT * FROM customer WHERE id = %s", (session['customer_id'],))
    customer = cursor.fetchone()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        promo_code = request.form.get('promo_code', '').strip()

        # 簡單後端驗證
        if len(name) < 1 or len(name) > 30:
            flash("姓名長度需在 1-30 字元之間。")
            return redirect(url_for('home.checkout.information'))
        if len(phone) < 8 or len(phone) > 20:
            flash("電話長度需在 8-20 碼之間。")
            return redirect(url_for('home.checkout.information'))
        if len(address) < 5 or len(address) > 100:
            flash("地址長度需在 5-100 字元之間。")
            return redirect(url_for('home.checkout.information'))
        
        # 驗證優惠碼
        if promo_code:
            cursor.execute("SELECT id FROM promo_code WHERE code = %s AND is_active = 1 AND is_deleted = 0", (promo_code,))
            if not cursor.fetchone():
                flash("無效的優惠碼，請重新輸入。")
                cursor.close()
                conn.close()
                return redirect(url_for('home.checkout.information'))

        # 暫存訂購資訊到 session
        session['checkout_info'] = {
            'name': name,
            'phone': phone,
            'region': request.form['region'],
            'locality': request.form['locality'],
            'address': address,
            'promo_code': promo_code
        }
        cursor.close()
        conn.close()
        return redirect(url_for('home.checkout.payment'))
    
    cursor.close()
    conn.close()
    return render_template('home/information.html', customer=customer)

@checkout_bp.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'customer_id' not in session or 'checkout_info' not in session:
        return redirect(url_for('checkout.information'))
    
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取購物車項目
    cursor.execute("""
        SELECT ci.qty, s.price, s.size, s.color, p.name as product_name, ci.sku_id
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN product p ON s.product_id = p.id
        WHERE ci.cart_id = %s
    """, (cart_id,))
    cart_items = cursor.fetchall()
    
    subtotal = sum(item['qty'] * item['price'] for item in cart_items)
    
    # 從資料庫獲取運費
    cursor.execute("SELECT fee FROM region WHERE name = %s", (session['checkout_info']['region'],))
    region_data = cursor.fetchone()
    shipping_fee = region_data['fee'] if region_data else 0
    
    # 計算折扣
    promo_code = session['checkout_info'].get('promo_code')
    discount = 0
    
    if promo_code:
        cursor.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1 AND is_deleted = 0", (promo_code,))
        promo = cursor.fetchone()
        if promo and subtotal >= promo['min_order_amount']:
            if promo['discount_type'] == 'subtotal_discount':
                discount = subtotal * (promo['discount_value'] / 100)
            elif promo['discount_type'] == 'subtotal_deduction':
                discount = promo['discount_value']
    
    total = subtotal - discount + shipping_fee
    
    if request.method == 'POST':
        session['payment_info'] = {'card_number': request.form['card_number']}
        cursor.close()
        conn.close()
        return redirect(url_for('home.checkout.place_order'))
        
    cursor.close()
    conn.close()
    return render_template('home/payment.html', 
                           cart_items=cart_items, 
                           subtotal=subtotal, 
                           discount=discount, 
                           shipping_fee=shipping_fee, 
                           total=total)

@checkout_bp.route('/place_order', methods=['GET', 'POST'])
def place_order():
    if 'customer_id' not in session or 'checkout_info' not in session or 'payment_info' not in session:
        return redirect(url_for('home.checkout.information'))
    
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. 重新驗證並獲取有效的購物車項目
    # 獲取購物車項目與計算總額
    cursor.execute("""
        SELECT ci.qty, s.id as sku_id, s.price, s.size, s.color, p.name as product_name, p.is_active, p.is_deleted, s.is_active as sku_is_active, s.is_deleted as sku_is_deleted
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN product p ON s.product_id = p.id
        WHERE ci.cart_id = %s
    """, (cart_id,))
    cart_items = cursor.fetchall()

    # 檢查購物車是否為空
    if not cart_items:
        cursor.close()
        conn.close()
        flash("您的購物車目前是空的，無法進行結帳。")
        return redirect(url_for('home.checkout.view_cart'))

    # 檢查商品或 SKU 是否下架/刪除
    for item in cart_items:
        if not item['is_active'] or item['is_deleted'] or not item['sku_is_active'] or item['sku_is_deleted']:
            cursor.close()
            conn.close()
            return "<script>alert('購物車中有商品已下架或刪除，請重新確認購物車！'); window.location.href='/view_cart';</script>"
    subtotal = sum(item['qty'] * item['price'] for item in cart_items)
    
    # 從資料庫獲取運費
    cursor.execute("SELECT fee FROM region WHERE name = %s", (session['checkout_info']['region'],))
    region_data = cursor.fetchone()
    shipping_fee = region_data['fee'] if region_data else 0
    
    # 2. 驗證優惠碼狀態
    promo_code = session['checkout_info'].get('promo_code')
    discount = 0
    promo_id = None
    if promo_code:
        cursor.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1 AND is_deleted = 0", (promo_code,))
        promo = cursor.fetchone()
        if not promo or subtotal < promo['min_order_amount']:
            cursor.close()
            conn.close()
            return "<script>alert('優惠碼已失效或不符合門檻，請重新確認！'); window.location.href='/checkout/information';</script>"
        
        promo_id = promo['id']
        if promo['discount_type'] == 'subtotal_discount':
            discount = subtotal * (promo['discount_value'] / 100)
        elif promo['discount_type'] == 'subtotal_deduction':
            discount = promo['discount_value']
    
    total = subtotal - discount + shipping_fee
    
    if request.method == 'POST':
        # 執行下單 (使用 Transaction)
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 插入訂單
            order_sql = """INSERT INTO orders (customer_id, subtotal, shipping_fee, discount_total, total, promo_code_id, promo_code_snapshot,
                           name, phone, region, locality, address, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(order_sql, (session['customer_id'], subtotal, shipping_fee, discount, total, promo_id, promo_code,
                                      session['checkout_info']['name'], session['checkout_info']['phone'], 
                                      session['checkout_info']['region'], session['checkout_info']['locality'], 
                                      session['checkout_info']['address'], now, now))
            order_id = cursor.lastrowid
            
            # 插入訂單明細
            for item in cart_items:
                cursor.execute("INSERT INTO order_item (order_id, sku_id, product_name, size, color, qty, price) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                               (order_id, item['sku_id'], item['product_name'], item['size'], item['color'], item['qty'], item['price']))
            
            # 插入付款記錄
            cursor.execute("INSERT INTO payment (order_id, method, card_number, status, paid_at) VALUES (%s, 'credit_card', %s, 'paid', %s)",
                           (order_id, session['payment_info']['card_number'], now))
            
            # 插入初始物流記錄 (pending: 未發貨)
            cursor.execute("INSERT INTO shipment (order_id, status) VALUES (%s, 'pending')", (order_id,))
            
            # 清空購物車項目並移除購物車記錄
            cursor.execute("DELETE FROM cart_item WHERE cart_id = %s", (cart_id,))
            cursor.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
            
            conn.commit()
            
            # 清理 session
            session.pop('checkout_info')
            session.pop('payment_info')
            
            return redirect(url_for('home.checkout.complete', order_id=order_id))
        except Exception as e:
            conn.rollback()
            return f"<script>alert('下單失敗，請稍後再試。'); window.location.href='/checkout/view_cart';</script>"
        finally:
            cursor.close()
            conn.close()
    
    cursor.close()
    conn.close()
    return render_template('home/place_order.html', 
                           cart_items=cart_items, 
                           info=session['checkout_info'],
                           subtotal=subtotal, 
                           discount=discount, 
                           shipping_fee=shipping_fee, 
                           total=total)

@checkout_bp.route('/complete/<int:order_id>')
def complete(order_id):
    return render_template('home/complete.html', order_id=order_id)


