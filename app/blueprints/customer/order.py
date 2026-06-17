from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.db import get_db_connection
from functools import wraps

customer_order_bp = Blueprint('customer_order', __name__)

# 身分驗證裝飾器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            flash("請先登入以檢視訂單")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@customer_order_bp.route('/list')
@login_required
def order_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 僅查詢該會員的訂單
    cursor.execute("""
        SELECT o.*, s.status as shipment_status
        FROM orders o
        LEFT JOIN shipment s ON o.id = s.order_id
        WHERE o.customer_id = %s
        ORDER BY o.created_at DESC
    """, (session['customer_id'],))
    orders = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('customer/order_list.html', orders=orders)

@customer_order_bp.route('/view/<int:id>')
@login_required
def order_view(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 檢查訂單歸屬權
    cursor.execute("SELECT * FROM orders WHERE id = %s AND customer_id = %s", (id, session['customer_id']))
    order = cursor.fetchone()
    
    if not order:
        cursor.close()
        conn.close()
        flash("找不到該訂單")
        return redirect(url_for('customer.customer_order.order_list'))

    # 獲取原始運費以計算運費折抵
    cursor.execute("SELECT fee FROM region WHERE name = %s", (order['region'],))
    region_data = cursor.fetchone()
    original_shipping_fee = region_data['fee'] if region_data else order['shipping_fee']
    shipping_discount = max(0, original_shipping_fee - order['shipping_fee'])

    # 獲取訂單項目...

    cursor.execute("""
        SELECT oi.*, 
               COALESCE(SUM(CASE WHEN rr.status IN ('requested', 'approved', 'refunded') THEN ri.qty ELSE 0 END), 0) as requested_qty,
               COALESCE(SUM(CASE WHEN rr.status = 'refunded' THEN ri.qty ELSE 0 END), 0) as returned_qty,
               (SELECT COUNT(id) FROM review WHERE order_item_id = oi.id) as is_reviewed
        FROM order_item oi
        LEFT JOIN return_item ri ON oi.id = ri.order_item_id
        LEFT JOIN return_request rr ON ri.return_request_id = rr.id
        WHERE oi.order_id = %s
        GROUP BY oi.id
    """, (id,))
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('customer/order_view.html', order=order, items=items, 
                         original_shipping_fee=original_shipping_fee, 
                         shipping_discount=shipping_discount)

@customer_order_bp.route('/cancel/<int:id>', methods=['POST'])
@login_required
def cancel_order(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 檢查訂單歸屬權與狀態 (僅限狀態為 'pending' 的訂單可取消)
    cursor.execute("""
        SELECT o.id FROM orders o 
        LEFT JOIN shipment s ON o.id = s.order_id
        WHERE o.id = %s AND o.customer_id = %s 
        AND (s.status = 'pending' OR s.status IS NULL)
        AND o.status != 'cancelled'
    """, (id, session['customer_id']))
    
    order = cursor.fetchone()
    if not order:
        cursor.close()
        conn.close()
        flash("此訂單無法取消 (可能已出貨或狀態不符)")
        return redirect(url_for('customer.customer_order.order_list'))
        
    try:
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", ('cancelled', id))
        conn.commit()
        flash(f"訂單 {id} 已成功取消")
    except Exception as e:
        conn.rollback()
        flash(f"取消失敗: {e}")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('customer.customer_order.order_list'))

# === 👇 新增：完成訂單 (確認收貨) API 👇 ===
@customer_order_bp.route('/complete/<int:id>', methods=['POST'])
@login_required
def complete_order(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 檢查訂單是否為 shipped 且屬於該用戶
        cursor.execute("""
            SELECT id FROM orders 
            WHERE id = %s AND customer_id = %s AND status = 'shipped'
        """, (id, session['customer_id']))
        
        if not cursor.fetchone():
            flash("無法完成此訂單，可能狀態不符或權限不足")
            return redirect(request.referrer)

        # 更新狀態為 completed
        cursor.execute("UPDATE orders SET status = 'completed', updated_at = NOW() WHERE id = %s", (id,))
        conn.commit()
        flash("訂單已完成！現在您可以為購買的商品填寫評價囉。")
        
    except Exception as e:
        conn.rollback()
        flash("系統錯誤，請稍後再試。")
    finally:
        cursor.close()
        conn.close()

    return redirect(request.referrer)