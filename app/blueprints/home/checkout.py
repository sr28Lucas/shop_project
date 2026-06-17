from flask import Blueprint, session, request, redirect, render_template, url_for, flash 
from app.db import get_db_connection
from datetime import datetime
from app.utils.validators import Validator

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

def calculate_order_totals(subtotal, shipping_fee, promo):
    subtotal_discount = 0
    shipping_discount = 0
    
    if not promo:
        return subtotal_discount, shipping_discount, shipping_fee
    
    if subtotal < promo['min_order_amount']:
        return subtotal_discount, shipping_discount, shipping_fee

    if promo['discount_type'] == 'subtotal_discount':
        subtotal_discount = round(subtotal * (promo['discount_value'] / 100))
    elif promo['discount_type'] == 'subtotal_deduction':
        subtotal_discount = round(promo['discount_value'])
    elif promo['discount_type'] == 'shipping_deduction':
        shipping_discount = min(shipping_fee, round(promo['discount_value']))
    elif promo['discount_type'] == 'free_shipping':
        shipping_discount = shipping_fee
        
    subtotal_discount = min(subtotal, subtotal_discount)
    final_shipping_fee = max(0, shipping_fee - shipping_discount)
        
    return subtotal_discount, shipping_discount, final_shipping_fee

def validate_promo_code(promo, subtotal=None):
    if not promo:
        return False, "優惠碼不存在或已失效。"
    
    now = datetime.now()
    
    if promo['start_at'] and now < promo['start_at']:
        return False, "優惠碼尚未開始。"
    if promo['end_at'] and now > promo['end_at']:
        return False, "優惠碼已過期。"
        
    if promo['usage_limit'] and promo['used_count'] >= promo['usage_limit']:
        return False, "優惠碼使用次數已達上限。"

    if subtotal is not None and subtotal < promo['min_order_amount']:
        return False, f"未達優惠碼最低消費金額 (需滿 ${promo['min_order_amount']:,.0f})。"
        
    return True, None

@checkout_bp.route('/view_cart')
def view_cart():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT ci.sku_id, p.name, v.color, s.size
        FROM cart_item ci
        JOIN sku s ON ci.sku_id = s.id
        JOIN variant v ON s.variant_id = v.id
        JOIN product p ON v.product_id = p.id
        WHERE ci.cart_id = %s
          AND (p.is_active = 0 OR p.is_deleted = 1 OR v.is_active = 0 OR v.is_deleted = 1 OR s.is_active = 0 OR s.is_deleted = 1)
    """, (cart_id,))
    inactive_items = cursor.fetchall()
    
    if inactive_items:
        inactive_sku_ids = [item['sku_id'] for item in inactive_items]
        format_strings = ','.join(['%s'] * len(inactive_sku_ids))
        cursor.execute(f"DELETE FROM cart_item WHERE cart_id = %s AND sku_id IN ({format_strings})", [cart_id] + inactive_sku_ids)
        conn.commit()
        item_names = [f"{item['name']} ({item['color']}/{item['size']})" for item in inactive_items]
        flash(f"以下商品或規格已下架或刪除，並從購物車移除：{', '.join(item_names)}")

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
          AND p.is_deleted = 0 AND v.is_deleted = 0 AND s.is_deleted = 0
    """, (cart_id,))
    cart_items = cursor.fetchall()
    
    subtotal = sum(item['qty'] * item['price'] for item in cart_items)

    recommend_query = """
        SELECT 
            p.id, p.name,
            (SELECT MIN(price) FROM sku s JOIN variant v ON s.variant_id = v.id WHERE v.product_id = p.id AND s.is_active = 1 AND s.is_deleted = 0) as min_price,
            (SELECT filename FROM image i WHERE i.product_id = p.id AND i.image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image,
            COALESCE((SELECT SUM(qty) FROM order_item WHERE product_id = p.id), 0) +
            COALESCE((
                SELECT SUM(ci.qty)
                FROM cart_item ci
                JOIN sku s ON ci.sku_id = s.id
                JOIN variant v ON s.variant_id = v.id
                WHERE v.product_id = p.id
            ), 0) as popularity_score
        FROM product p
        WHERE p.is_active = 1 AND p.is_deleted = 0
        HAVING popularity_score > 0
        ORDER BY popularity_score DESC
        LIMIT 4;
    """
    cursor.execute(recommend_query)
    recommended_products = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('home/cart.html', cart_items=cart_items, subtotal=subtotal, recommended_products=recommended_products)

@checkout_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'customer_id' not in session:
        return {'success': False, 'message': '請先登入'}, 401
    
    sku_id = request.form.get('sku_id')
    try:
        qty = int(request.form.get('qty', 1))
    except ValueError:
        return {'success': False, 'message': '無效的數量'}, 400
        
    if not sku_id or qty <= 0:
        return {'success': False, 'message': '請選擇有效的規格與數量'}, 400
        
    if qty > 999:
        return {'success': False, 'message': '單次加入數量不能超過 999'}, 400
        
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT stock FROM sku WHERE id = %s", (sku_id,))
    sku_data = cursor.fetchone()
    if not sku_data:
        cursor.close()
        conn.close()
        return {'success': False, 'message': '商品不存在'}, 404
        
    if sku_data['stock'] < qty:
        cursor.close()
        conn.close()
        return {'success': False, 'message': f'庫存不足，剩餘 {sku_data["stock"]} 件'}, 400
    
    cursor.execute("SELECT qty FROM cart_item WHERE cart_id = %s AND sku_id = %s", (cart_id, sku_id))
    item = cursor.fetchone()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        if item:
            if sku_data['stock'] < item['qty'] + qty:
                cursor.close()
                conn.close()
                return {'success': False, 'message': f'庫存不足，無法再加入 {qty} 件'}, 400
            
            cursor.execute("UPDATE cart_item SET qty = qty + %s, updated_at = %s WHERE cart_id = %s AND sku_id = %s",
                           (qty, now, cart_id, sku_id))
        else:
            cursor.execute("INSERT INTO cart_item (cart_id, sku_id, qty, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
                           (cart_id, sku_id, qty, now, now))
        conn.commit()
        return {'success': True, 'message': '已加入購物車'}
    except Exception as e:
        conn.rollback()
        return {'success': False, 'message': f'加入購物車失敗: {e}'}, 500
    finally:
        cursor.close()
        conn.close()

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
    
    if qty > 999:
        flash("數量不能超過 999")
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
    
    cursor.execute("""
        SELECT c.*, r.name as region, l.name as locality 
        FROM customer c
        LEFT JOIN region r ON c.region_id = r.id
        LEFT JOIN locality l ON c.locality_id = l.id
        WHERE c.id = %s
    """, (session['customer_id'],))
    customer = cursor.fetchone()
    
    if request.method == 'POST':
        selected_skus = request.form.getlist('selected_skus')
        if selected_skus:
            session['selected_sku_ids'] = [int(sid) for sid in selected_skus]
        
        if 'selected_sku_ids' not in session or not session['selected_sku_ids']:
            flash("請先選擇要結帳的商品")
            return redirect(url_for('home.checkout.view_cart'))

        cart_id = get_active_cart(session['customer_id'])
        format_strings = ','.join(['%s'] * len(session['selected_sku_ids']))
        cursor.execute(f"""
            SELECT ci.qty, s.stock, s.price, p.name as product_name, v.color, s.size
            FROM cart_item ci
            JOIN sku s ON ci.sku_id = s.id
            JOIN variant v ON s.variant_id = v.id
            JOIN product p ON v.product_id = p.id
            WHERE ci.sku_id IN ({format_strings}) AND ci.cart_id = %s
        """, session['selected_sku_ids'] + [cart_id])
        items_to_check = cursor.fetchall()

        for item in items_to_check:
            if item['qty'] > item['stock']:
                flash(f"商品 {item['product_name']} ({item['color']}/{item['size']}) 庫存不足，目前剩餘 {item['stock']}。")
                cursor.close()
                conn.close()
                return redirect(url_for('home.checkout.view_cart'))

        if not request.form.get('name'):
            cursor.close()
            conn.close()
            return render_template('home/information.html', customer=customer)

        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        promo_code = request.form.get('promo_code', '').strip()
        region = request.form.get('region', '')
        locality = request.form.get('locality', '')

        # Server-side validation
        if not name or len(name) > 30:
            flash("請輸入有效的姓名 (1-30 字元)。")
        elif not phone or not phone.isdigit() or len(phone) < 8 or len(phone) > 20:
            flash("請輸入有效的電話號碼 (8-20 位數字)。")
        elif not region or not locality:
            flash("請選擇配送的縣市與鄉鎮市區。")
        elif not address or len(address) < 5 or len(address) > 100:
            flash("請輸入有效的詳細地址 (5-100 字元)。")
        else:
            # 額外驗證優惠碼 (不通過則留在本頁，不跳轉)
            if promo_code:
                cursor.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1 AND is_deleted = 0", (promo_code,))
                promo = cursor.fetchone()
                if promo:
                    # 計算目前的 subtotal 以驗證門檻
                    subtotal = sum(item['qty'] * item['price'] for item in items_to_check)
                    is_valid, promo_err = validate_promo_code(promo, subtotal)
                    if not is_valid:
                        flash(promo_err)
                        cursor.close()
                        conn.close()
                        return render_template('home/information.html', customer=customer, 
                                             temp_info={'name': name, 'phone': phone, 'address': address, 'promo_code': promo_code, 'region': region, 'locality': locality})
                else:
                    flash("優惠碼無效或不存在。")
                    cursor.close()
                    conn.close()
                    return render_template('home/information.html', customer=customer, 
                                         temp_info={'name': name, 'phone': phone, 'address': address, 'promo_code': promo_code, 'region': region, 'locality': locality})

            session['checkout_info'] = {'name': name, 'phone': phone, 'region': region, 'locality': locality, 'address': address, 'promo_code': promo_code}
            cursor.close()
            conn.close()
            return redirect(url_for('home.checkout.payment'))
        
        cursor.close()
        conn.close()
        return render_template('home/information.html', customer=customer, 
                                 temp_info={'name': name, 'phone': phone, 'address': address, 'promo_code': promo_code, 'region': region, 'locality': locality})
    
    cursor.close()
    conn.close()
    return render_template('home/information.html', customer=customer)

@checkout_bp.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'customer_id' not in session or 'checkout_info' not in session:
        return redirect(url_for('home.checkout.information'))
    
    cart_id = get_active_cart(session['customer_id'])
    conn = get_db_connection()
    
    try:
        with conn.cursor(dictionary=True) as cursor:
            selected_ids = session.get('selected_sku_ids', [])
            if not selected_ids:
                conn.close()
                return redirect(url_for('home.checkout.view_cart'))
                
            format_strings = ','.join(['%s'] * len(selected_ids))
            cursor.execute(f"""
                SELECT ci.qty, s.price, s.size, v.color, p.name as product_name, ci.sku_id,
                COALESCE(
                    (SELECT filename FROM image WHERE variant_id = v.id LIMIT 1),
                    (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1)
                ) as image
                FROM cart_item ci
                JOIN sku s ON ci.sku_id = s.id
                JOIN variant v ON s.variant_id = v.id
                JOIN product p ON v.product_id = p.id
                WHERE ci.cart_id = %s AND ci.sku_id IN ({format_strings})
            """, [cart_id] + selected_ids)
            cart_items = cursor.fetchall()
        
        subtotal = sum(item['qty'] * item['price'] for item in cart_items)
        
        shipping_fee = 0
        with conn.cursor(dictionary=True) as cursor_region:
            cursor_region.execute("SELECT fee FROM region WHERE name = %s", (session['checkout_info']['region'],))
            region_data = cursor_region.fetchone()
            if region_data:
                shipping_fee = region_data['fee']
        
        promo_code = session['checkout_info'].get('promo_code')
        promo = None
        if promo_code:
            with conn.cursor(dictionary=True) as cursor_promo:
                cursor_promo.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1 AND is_deleted = 0", (promo_code,))
                promo = cursor_promo.fetchone()
            
            if promo:
                is_valid, error = validate_promo_code(promo, subtotal)
                if not is_valid:
                    flash(error)
                    promo = None
                    session['checkout_info'].pop('promo_code', None)
            else:
                flash("優惠碼無效")
                promo = None
                session['checkout_info'].pop('promo_code', None)
        
        discount, shipping_discount, shipping_fee = calculate_order_totals(subtotal, shipping_fee, promo)
        total = subtotal - discount + shipping_fee
        
        if request.method == 'POST':
            card_number = request.form.get('card_number')
            if not Validator.is_valid_credit_card(card_number):
                flash("無效的信用卡號，必須為 16 碼數字。")
                conn.close()
                return render_template('home/payment.html', cart_items=cart_items, subtotal=subtotal, discount=discount, shipping_discount=shipping_discount, shipping_fee=shipping_fee, total=total)

            session['payment_info'] = {'card_number': card_number}
            conn.close()
            return redirect(url_for('home.checkout.place_order'))
            
        conn.close()
        return render_template('home/payment.html', cart_items=cart_items, subtotal=subtotal, discount=discount, shipping_discount=shipping_discount, shipping_fee=shipping_fee, total=total)
    except Exception as e:
        conn.close()
        raise e

@checkout_bp.route('/place_order', methods=['GET', 'POST'])
def place_order():
    if 'customer_id' not in session or 'checkout_info' not in session or 'payment_info' not in session:
        return redirect(url_for('home.checkout.information'))

    cart_id = get_active_cart(session['customer_id'])
    selected_ids = session.get('selected_sku_ids', [])
    if not selected_ids:
        return redirect(url_for('home.checkout.view_cart'))

    conn = get_db_connection()
    
    try:
        # 建立專用游標
        with conn.cursor(dictionary=True) as cursor:
            # 獲取購物車項目
            format_strings = ','.join(['%s'] * len(selected_ids))
            cursor.execute(f"""
                SELECT ci.qty, s.id as sku_id, s.sku_code, s.price, s.cost, s.size, s.stock, v.color, v.id as variant_id, p.name as product_name, p.id as product_id,
                COALESCE(
                    (SELECT filename FROM image WHERE variant_id = v.id LIMIT 1),
                    (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1)
                ) as image
                FROM cart_item ci
                JOIN sku s ON ci.sku_id = s.id
                JOIN variant v ON s.variant_id = v.id
                JOIN product p ON v.product_id = p.id
                WHERE ci.cart_id = %s AND ci.sku_id IN ({format_strings})
                FOR UPDATE
            """, [cart_id] + selected_ids)
            cart_items = cursor.fetchall()

        if not cart_items:
            conn.close()
            flash("您選擇的商品目前無法結帳。")
            return redirect(url_for('home.checkout.view_cart'))
        
        # 檢查庫存與資料完整性
        for item in cart_items:
            if not item.get('product_name') or item.get('price') is None or item.get('stock') is None:
                conn.close()
                flash("購物車中有商品資料異常，無法結帳。")
                return redirect(url_for('home.checkout.view_cart'))
                
            if item['qty'] > item['stock']:
                conn.close()
                flash(f"商品 {item['product_name']} ({item['color']}/{item['size']}) 庫存不足，目前剩餘 {item['stock']}。")
                return redirect(url_for('home.checkout.view_cart'))

        subtotal = sum(item['qty'] * item['price'] for item in cart_items)
        
        # 獲取運費
        shipping_fee = 0
        with conn.cursor(dictionary=True) as cursor_fee:
            cursor_fee.execute("SELECT fee FROM region WHERE name = %s", (session['checkout_info']['region'],))
            region_data = cursor_fee.fetchone()
            if region_data:
                shipping_fee = region_data['fee']
        
        # 處理優惠碼
        promo_code = session['checkout_info'].get('promo_code')
        promo = None
        if promo_code:
            with conn.cursor(dictionary=True) as cursor_promo:
                cursor_promo.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1 AND is_deleted = 0 FOR UPDATE", (promo_code,))
                promo = cursor_promo.fetchone()
            
            if promo:
                is_valid, error = validate_promo_code(promo, subtotal)
                if not is_valid:
                    flash(error)
                    promo = None
        
        discount_total, shipping_discount, shipping_fee = calculate_order_totals(subtotal, shipping_fee, promo)
        total = subtotal - discount_total + shipping_fee

        if total > 999999999:
            conn.close()
            flash("訂單總額超過系統限制。")
            return redirect(url_for('home.checkout.view_cart'))
        
        if request.method == 'POST':
            # --- 執行結帳 (真正下單) ---
            with conn.cursor() as cursor:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                # 插入訂單
                cursor.execute("""INSERT INTO orders (customer_id, subtotal, shipping_fee, discount_total, total, promo_code_id, promo_code_snapshot,
                               name, phone, region, locality, address, created_at, updated_at)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                               (session['customer_id'], subtotal, shipping_fee, discount_total, total, promo['id'] if promo else None, promo_code,
                                session['checkout_info']['name'], session['checkout_info']['phone'], 
                                session['checkout_info']['region'], session['checkout_info']['locality'], 
                                session['checkout_info']['address'], now, now))
                order_id = cursor.lastrowid

                # 如果有優惠碼，更新使用次數
                if promo:
                    cursor.execute("UPDATE promo_code SET used_count = used_count + 1 WHERE id = %s", (promo['id'],))

                # 計算折扣比例
                discount_rate = discount_total / subtotal if subtotal > 0 else 0

                # 插入訂單明細，並扣除庫存
                for item in cart_items:
                    cursor.execute("UPDATE sku SET stock = stock - %s WHERE id = %s", (item['qty'], item['sku_id']))

                    unit_price = max(0, item['price'] * (1 - discount_rate))

                    cursor.execute("""INSERT INTO order_item (order_id, product_id, variant_id, sku_id, product_name, variant_name, sku_code, size, color, qty, original_price, unit_price, unit_cost) 
                                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                                   (order_id, item['product_id'], item['variant_id'], item['sku_id'], item['product_name'], item['product_name'], item['sku_code'], item['size'], item['color'], item['qty'], item['price'], unit_price, item['cost']))

                # 插入付款記錄
                cursor.execute("INSERT INTO payment (order_id, method, card_number, status, paid_at) VALUES (%s, 'credit_card', %s, 'paid', %s)",
                               (order_id, session['payment_info']['card_number'], now))

                # 插入貨運記錄
                cursor.execute("INSERT INTO shipment (order_id, status) VALUES (%s, 'pending')", (order_id,))

                # 刪除購物車項目
                cursor.execute(f"DELETE FROM cart_item WHERE cart_id = %s AND sku_id IN ({format_strings})", [cart_id] + selected_ids)

                # 清理購物車
                cursor.execute("SELECT 1 FROM cart_item WHERE cart_id = %s", (cart_id,))
                if not cursor.fetchone():
                    cursor.execute("DELETE FROM cart WHERE id = %s", (cart_id,))

                conn.commit()
                
            session.pop('checkout_info')
            session.pop('payment_info')
            session.pop('selected_sku_ids', None)
            conn.close()
            return redirect(url_for('home.checkout.complete', order_id=order_id))
        
        # GET 請求：顯示確認頁面 (下單前檢查介面)
        conn.close()
        return render_template('home/place_order.html',
                               cart_items=cart_items,
                               info=session['checkout_info'],
                               subtotal=subtotal,
                               discount=discount_total,
                               shipping_discount=shipping_discount,
                               shipping_fee=shipping_fee,
                               total=total)

    except Exception as e:
        # 嘗試回滾，但若連線已斷開則跳過
        try:
            if conn.is_connected():
                conn.rollback()
        except:
            pass
        conn.close()
        print(f"DEBUG: 下單錯誤: {e}")
        return f"<script>alert('下單失敗，請稍後再試。'); window.location.href='/checkout/view_cart';</script>"

@checkout_bp.route('/complete/<int:order_id>')
def complete(order_id):
    return render_template('home/complete.html', order_id=order_id)

