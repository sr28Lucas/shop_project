from flask import Blueprint, session, request, redirect, render_template, url_for, flash 
from app.db import get_db_connection
from datetime import datetime

checkout_bp = Blueprint('checkout', __name__)

def get_active_cart(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM cart WHERE customer_id = %s", (customer_id,))
    cart = cursor.fetchone()
    if not cart:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO cart (customer_id, created_at, updated_at) VALUES (%s, %s, %s)",
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
    
    # 1. 檢查並清除已下架的商品或規格
    cursor.execute("""
        SELECT ci.sku_id, p.name, v.color, s.size
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN variant v ON s.variant_id = v.id
        JOIN product p ON v.product_id = p.id
        WHERE ci.cart_id = %s
          AND (p.is_active = 0 OR v.is_active = 0 OR s.is_active = 0)
    """, (cart_id,))
    inactive_items = cursor.fetchall()
    
    if inactive_items:
        # 刪除這些項目
        inactive_sku_ids = [item['sku_id'] for item in inactive_items]
        format_strings = ','.join(['%s'] * len(inactive_sku_ids))
        cursor.execute(f"DELETE FROM cart_item WHERE cart_id = %s AND sku_id IN ({format_strings})", [cart_id] + inactive_sku_ids)
        conn.commit()
        
        # 提示使用者
        item_names = [f"{item['name']} ({item['color']}/{item['size']})" for item in inactive_items]
        flash(f"以下商品或規格已下架並從購物車移除：{', '.join(item_names)}")

    # 2. 獲取剩餘有效的購物車項目
    cursor.execute("""
        SELECT ci.qty, s.price, s.size, s.stock, v.color, p.name as product_name, ci.sku_id, p.id as product_id,
        COALESCE(
            (SELECT filename FROM image WHERE variant_id = v.id LIMIT 1),
            (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1)
        ) as image
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN variant v ON s.variant_id = v.id
        JOIN product p ON v.product_id = p.id
        WHERE ci.cart_id = %s
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
    try:
        qty = int(request.form.get('qty', 1))
    except ValueError:
        return "<script>alert('無效的數量！'); window.history.back();</script>"
        
    if not sku_id or qty <= 0:
        return "<script>alert('請選擇有效的規格與數量！'); window.history.back();</script>"
        
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
    try:
        qty = int(request.form['qty'])
    except ValueError:
        flash("無效的數量")
        return redirect(url_for('home.checkout.view_cart'))

    if qty <= 0:
        flash("數量必須大於 0")
        return redirect(url_for('home.checkout.view_cart'))

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
    
    # 獲取會員資料，包含地區與鄉鎮名稱
    cursor.execute("""
        SELECT c.*, r.name as region, l.name as locality 
        FROM customer c
        LEFT JOIN region r ON c.region_id = r.id
        LEFT JOIN locality l ON c.locality_id = l.id
        WHERE c.id = %s
    """, (session['customer_id'],))
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
        
        # 驗證優惠碼，移除 is_deleted
        if promo_code:
            cursor.execute("SELECT id FROM promo_code WHERE code = %s AND is_active = 1", (promo_code,))
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
    
    # 獲取購物車項目，增加圖片獲取
    cursor.execute("""
        SELECT ci.qty, s.price, s.size, v.color, p.name as product_name, ci.sku_id,
        COALESCE(
            (SELECT filename FROM image WHERE variant_id = v.id LIMIT 1),
            (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1)
        ) as image
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN variant v ON s.variant_id = v.id
        JOIN product p ON v.product_id = p.id
        WHERE ci.cart_id = %s
    """, (cart_id,))
    cart_items = cursor.fetchall()
    
    subtotal = sum(item['qty'] * item['price'] for item in cart_items)
    
    # 從資料庫獲取運費
    cursor.execute("SELECT fee FROM region WHERE name = %s", (session['checkout_info']['region'],))
    region_data = cursor.fetchone()
    shipping_fee = region_data['fee'] if region_data else 0
    
    # 計算折扣，移除 is_deleted
    promo_code = session['checkout_info'].get('promo_code')
    discount = 0
    
    if promo_code:
        cursor.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1", (promo_code,))
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
    
    # 獲取有效的購物車項目，增加圖片獲取
    cursor.execute("""
        SELECT ci.qty, s.id as sku_id, s.sku_code, s.price, s.size, s.stock, v.color, v.id as variant_id, p.name as product_name, p.id as product_id,
        COALESCE(
            (SELECT filename FROM image WHERE variant_id = v.id LIMIT 1),
            (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1)
        ) as image
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN variant v ON s.variant_id = v.id
        JOIN product p ON v.product_id = p.id
        WHERE ci.cart_id = %s
    """, (cart_id,))
    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close()
        conn.close()
        flash("您的購物車目前是空的，無法進行結帳。")
        return redirect(url_for('home.checkout.view_cart'))
    
    # 檢查庫存
    for item in cart_items:
        if item['qty'] > item['stock']:
            cursor.close()
            conn.close()
            flash(f"商品 {item['product_name']} ({item['color']}/{item['size']}) 庫存不足，剩餘 {item['stock']}。")
            return redirect(url_for('home.checkout.view_cart'))

    subtotal = sum(item['qty'] * item['price'] for item in cart_items)
    
    cursor.execute("SELECT fee FROM region WHERE name = %s", (session['checkout_info']['region'],))
    region_data = cursor.fetchone()
    shipping_fee = region_data['fee'] if region_data else 0
    
    promo_code = session['checkout_info'].get('promo_code')
    discount = 0
    promo_id = None
    if promo_code:
        cursor.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1", (promo_code,))
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
            
            # 插入訂單明細，並扣除庫存
            for item in cart_items:
                # 再次檢查庫存並鎖定行 (可選，但在這裡先簡單處理)
                cursor.execute("UPDATE sku SET stock = stock - %s WHERE id = %s", (item['qty'], item['sku_id']))
                
                cursor.execute("""INSERT INTO order_item (order_id, product_id, variant_id, sku_id, product_name, variant_name, sku_code, size, color, qty, price) 
                                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                               (order_id, item['product_id'], item['variant_id'], item['sku_id'], item['product_name'], item['color'], item['sku_code'], item['size'], item['color'], item['qty'], item['price']))
            
            # 插入付款記錄
            cursor.execute("INSERT INTO payment (order_id, method, card_number, status, paid_at) VALUES (%s, 'credit_card', %s, 'paid', %s)",
                           (order_id, session['payment_info']['card_number'], now))
            
            cursor.execute("INSERT INTO shipment (order_id, status) VALUES (%s, 'pending')", (order_id,))
            
            cursor.execute("DELETE FROM cart_item WHERE cart_id = %s", (cart_id,))
            cursor.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
            
            conn.commit()
            
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



