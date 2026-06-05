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
    """
    Helper to calculate discount and adjusted shipping fee based on promo.
    Returns (discount_total, shipping_fee)
    """
    discount_total = 0
    if not promo:
        return discount_total, shipping_fee
    
    if subtotal < promo['min_order_amount']:
        return discount_total, shipping_fee

    if promo['discount_type'] == 'subtotal_discount':
        discount_total = round(subtotal * (promo['discount_value'] / 100))
    elif promo['discount_type'] == 'subtotal_deduction':
        discount_total = round(promo['discount_value'])
    elif promo['discount_type'] == 'shipping_deduction':
        shipping_fee = max(0, shipping_fee - round(promo['discount_value']))
    elif promo['discount_type'] == 'free_shipping':
        shipping_fee = 0
        
    return discount_total, shipping_fee

def validate_promo_code(promo):
    if not promo:
        return False, "優惠碼不存在或已失效。"
    
    now = datetime.now()
    
    # 時間檢查
    if promo['start_at'] and now < promo['start_at']:
        return False, "優惠碼尚未開始。"
    if promo['end_at'] and now > promo['end_at']:
        return False, "優惠碼已過期。"
        
    # 使用次數檢查
    if promo['usage_limit'] and promo['used_count'] >= promo['usage_limit']:
        return False, "優惠碼使用次數已達上限。"
        
    return True, None

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

    # === 3. 新增：撈取「大家都在看」的推薦商品 ===
    recommend_query = """
        SELECT 
            p.id, p.name, 
            (SELECT price FROM sku s JOIN variant v ON s.variant_id = v.id WHERE v.product_id = p.id AND s.is_active != 0 ORDER BY price ASC LIMIT 1) as min_price,
            (SELECT filename FROM image i WHERE i.product_id = p.id AND i.image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image
        FROM product p
        WHERE p.is_active != 0
        ORDER BY (SELECT COUNT(*) FROM wishlist_item wi WHERE wi.product_id = p.id) DESC
        LIMIT 4;
    """
    cursor.execute(recommend_query)
    recommended_products = cursor.fetchall()
    # ==========================================
    
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
        
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 檢查庫存
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
    
    # Check if item exists
    cursor.execute("SELECT qty FROM cart_item WHERE cart_id = %s AND sku_id = %s", (cart_id, sku_id))
    item = cursor.fetchone()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        if item:
            # 檢查更新後的總數量是否超過庫存
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
        selected_skus = request.form.getlist('selected_skus')
        if selected_skus:
            session['selected_sku_ids'] = [int(sid) for sid in selected_skus]

            # 如果是從購物車「前往結帳」過來的，通常只會有 selected_skus，沒有姓名地址
            # 檢查是否包含姓名，若無，則視為「切換至填寫資訊頁面」，不進行驗證
            if not request.form.get('name'):
                cursor.close()
                conn.close()
                return render_template('home/information.html', customer=customer)
        
        # 檢查是否有勾選商品
        if 'selected_sku_ids' not in session or not session['selected_sku_ids']:
            flash("請先選擇要結帳的商品")
            return redirect(url_for('home.checkout.view_cart'))

        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        promo_code = request.form.get('promo_code', '').strip()
        region = request.form.get('region', '')
        locality = request.form.get('locality', '')

        # 簡單後端驗證
        error = None
        if len(name) < 1 or len(name) > 30:
            error = "姓名長度需在 1-30 字元之間。"
        elif len(phone) < 8 or len(phone) > 20:
            error = "電話長度需在 8-20 碼之間。"
        elif len(address) < 5 or len(address) > 100:
            error = "地址長度需在 5-100 字元之間。"
        
        if not error and promo_code:
            cursor.execute("SELECT id FROM promo_code WHERE code = %s AND is_active = 1", (promo_code,))
            if not cursor.fetchone():
                error = "無效的優惠碼，請重新輸入。"

        if error:
            flash(error)
            # 準備傳回前端的暫存資訊
            temp_info = {
                'name': name, 'phone': phone, 'address': address,
                'promo_code': promo_code, 'region': region, 'locality': locality
            }
            cursor.close()
            conn.close()
            return render_template('home/information.html', customer=customer, temp_info=temp_info)

        # 暫存訂購資訊到 session
        session['checkout_info'] = {
            'name': name, 'phone': phone, 'region': region,
            'locality': locality, 'address': address, 'promo_code': promo_code
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
        return redirect(url_for('home.checkout.information'))
    
    cart_id = get_active_cart(session['customer_id'])
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取購物車項目 (僅限勾選的)，增加圖片獲取
    selected_ids = session.get('selected_sku_ids', [])
    if not selected_ids:
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
    
    # 從資料庫獲取運費
    cursor.execute("SELECT fee FROM region WHERE name = %s", (session['checkout_info']['region'],))
    region_data = cursor.fetchone()
    shipping_fee = region_data['fee'] if region_data else 0
    
    # 計算折扣，移除 is_deleted
    promo_code = session['checkout_info'].get('promo_code')
    promo = None
    if promo_code:
        cursor.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1", (promo_code,))
        promo = cursor.fetchone()
        is_valid, error = validate_promo_code(promo)
        if not is_valid:
            flash(error)
            promo = None
            session['checkout_info'].pop('promo_code', None)
    
    discount, shipping_fee = calculate_order_totals(subtotal, shipping_fee, promo)
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
    selected_ids = session.get('selected_sku_ids', [])
    if not selected_ids:
        return redirect(url_for('home.checkout.view_cart'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 獲取有效的購物車項目 (僅限勾選的)，增加圖片與成本獲取
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
    """, [cart_id] + selected_ids)
    cart_items = cursor.fetchall()

    if not cart_items:
        cursor.close()
        conn.close()
        flash("您選擇的商品目前無法結帳。")
        return redirect(url_for('home.checkout.view_cart'))
    
    # 檢查庫存
    for item in cart_items:
        if item['qty'] > item['stock']:
            cursor.close()
            conn.close()
            flash(f"商品 {item['product_name']} ({item['color']}/{item['size']}) 庫存不足，剩餘 {item['stock']}。")
            return redirect(url_for('home.checkout.view_cart'))

    # 計算原價小計 (subtotal)
    subtotal = sum(item['qty'] * item['price'] for item in cart_items)
    
    cursor.execute("SELECT fee FROM region WHERE name = %s", (session['checkout_info']['region'],))
    region_data = cursor.fetchone()
    shipping_fee = region_data['fee'] if region_data else 0
    
    promo_code = session['checkout_info'].get('promo_code')
    promo = None
    if promo_code:
        cursor.execute("SELECT * FROM promo_code WHERE code = %s AND is_active = 1", (promo_code,))
        promo = cursor.fetchone()
        is_valid, error = validate_promo_code(promo)
        if not is_valid:
            # 如果優惠碼失效，在確認頁面提示並清除
            flash(error)
            promo = None
            session['checkout_info'].pop('promo_code', None)
        
    # 計算折扣與運費
    discount_total, shipping_fee = calculate_order_totals(subtotal, shipping_fee, promo)
    promo_id = promo['id'] if promo else None
    
    # 計算最終總計 (total)
    total = subtotal - discount_total + shipping_fee
    
    if request.method == 'POST':
        try:
            # 再次獲取購物車項目並鎖定庫存 (FOR UPDATE)
            cursor.execute(f"""
                SELECT ci.qty, s.id as sku_id, s.stock, s.price, s.cost, p.name as product_name, v.color, s.size
                FROM cart_item ci
                JOIN sku s ON ci.sku_id = s.id
                JOIN variant v ON s.variant_id = v.id
                JOIN product p ON v.product_id = p.id
                WHERE ci.cart_id = %s AND ci.sku_id IN ({format_strings})
                FOR UPDATE
            """, [cart_id] + selected_ids)
            locked_items = cursor.fetchall()
            
            # 1. 最終在庫存鎖定狀態下檢查庫存
            for item in locked_items:
                if item['qty'] > item['stock']:
                    conn.rollback()
                    flash(f"商品 {item['product_name']} ({item['color']}/{item['size']}) 在您結帳時已被搶購一空或數量不足。")
                    return redirect(url_for('home.checkout.view_cart'))
            
            # 2. 重新驗證並鎖定優惠碼
            if promo_id:
                cursor.execute("SELECT * FROM promo_code WHERE id = %s FOR UPDATE", (promo_id,))
                promo = cursor.fetchone()
                is_valid, error = validate_promo_code(promo)
                if not is_valid:
                    conn.rollback()
                    flash(error)
                    return redirect(url_for('home.checkout.view_cart'))
                
                # 更新使用次數
                cursor.execute("UPDATE promo_code SET used_count = used_count + 1 WHERE id = %s", (promo_id,))
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 插入訂單
            order_sql = """INSERT INTO orders (customer_id, subtotal, shipping_fee, discount_total, total, promo_code_id, promo_code_snapshot,
                           name, phone, region, locality, address, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(order_sql, (session['customer_id'], subtotal, shipping_fee, discount_total, total, promo_id, promo_code,
                                      session['checkout_info']['name'], session['checkout_info']['phone'], 
                                      session['checkout_info']['region'], session['checkout_info']['locality'], 
                                      session['checkout_info']['address'], now, now))
            order_id = cursor.lastrowid
            
            # 計算折扣比例
            discount_rate = discount_total / subtotal if subtotal > 0 else 0
            
            # 插入訂單明細，並扣除庫存
            for item in cart_items:
                # 扣除庫存
                cursor.execute("UPDATE sku SET stock = stock - %s WHERE id = %s", (item['qty'], item['sku_id']))
                
                # 計算單價
                original_price = item['price']
                unit_price = original_price * (1 - discount_rate)
                
                cursor.execute("""INSERT INTO order_item (order_id, product_id, variant_id, sku_id, product_name, variant_name, sku_code, size, color, qty, original_price, unit_price, unit_cost) 
                                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                               (order_id, item['product_id'], item['variant_id'], item['sku_id'], item['product_name'], item['color'], item['sku_code'], item['size'], item['color'], item['qty'], original_price, unit_price, item['cost']))
            
            # 插入付款記錄
            cursor.execute("INSERT INTO payment (order_id, method, card_number, status, paid_at) VALUES (%s, 'credit_card', %s, 'paid', %s)",
                           (order_id, session['payment_info']['card_number'], now))
            
            cursor.execute("INSERT INTO shipment (order_id, status) VALUES (%s, 'pending')", (order_id,))
            
            # 僅刪除已結帳項目
            cursor.execute(f"DELETE FROM cart_item WHERE cart_id = %s AND sku_id IN ({format_strings})", [cart_id] + selected_ids)
            
            # 檢查購物車是否還有剩餘商品，若無則刪除 cart
            cursor.execute("SELECT 1 FROM cart_item WHERE cart_id = %s", (cart_id,))
            if not cursor.fetchone():
                cursor.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
            
            conn.commit()
            
            session.pop('checkout_info')
            session.pop('payment_info')
            session.pop('selected_sku_ids', None) # 清除勾選狀態
            
            return redirect(url_for('home.checkout.complete', order_id=order_id))
        except Exception as e:
            conn.rollback()
            print(f"DEBUG: 下單錯誤: {e}")
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
                           discount=discount_total, 
                           shipping_fee=shipping_fee, 
                           total=total)

@checkout_bp.route('/complete/<int:order_id>')
def complete(order_id):
    return render_template('home/complete.html', order_id=order_id)