from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.db import get_db_connection
from datetime import datetime
from functools import wraps

customer_return_bp = Blueprint('customer_return', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'customer_id' not in session:
            flash("請先登入")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@customer_return_bp.route('/apply/<int:order_id>', methods=['GET', 'POST'])
@login_required
def apply(order_id):
    customer_id = session['customer_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. 檢查訂單是否存在且屬於該會員，且狀態為可退貨 (shipped, completed)
    cursor.execute("""
        SELECT * FROM orders 
        WHERE id = %s AND customer_id = %s 
        AND status IN ('shipped', 'completed')
    """, (order_id, customer_id))
    order = cursor.fetchone()

    if not order:
        cursor.close()
        conn.close()
        flash("找不到該訂單，或該訂單目前狀態無法申請退貨")
        return redirect(url_for('customer.customer_order.order_list'))

    # 2. 移除單一訂單僅限一次退貨的限制，改為檢查已退貨數量
    # 檢查該訂單中每個項目的累計退貨數量 (排除已拒絕的) 是否超過原始購買數量
    cursor.execute("""
        SELECT oi.id, oi.qty as original_qty, 
               COALESCE(SUM(CASE WHEN rr.status != 'rejected' THEN ri.qty ELSE 0 END), 0) as returned_qty
        FROM order_item oi
        LEFT JOIN return_item ri ON oi.id = ri.order_item_id
        LEFT JOIN return_request rr ON ri.return_request_id = rr.id
        WHERE oi.order_id = %s
        GROUP BY oi.id
    """, (order_id,))
    item_return_status = {row['id']: row for row in cursor.fetchall()}

    if request.method == 'POST':
        item_ids = request.form.getlist('item_ids') # order_item.id
        overall_reason = request.form.get('overall_reason')

        if not item_ids:
            flash("請至少選擇一項要退貨的商品")
        else:
            try:
                now = datetime.now()
                # 建立退貨主表
                cursor.execute("""
                    INSERT INTO return_request (order_id, status, reason, requested_at, created_at, updated_at)
                    VALUES (%s, 'requested', %s, %s, %s, %s)
                """, (order_id, overall_reason, now, now, now))
                return_request_id = cursor.lastrowid

                # 建立退貨明細並驗證數量
                for oi_id in item_ids:
                    qty = int(request.form.get(f'qty_{oi_id}', 0))
                    reason = request.form.get(f'reason_{oi_id}', '')
                    
                    if qty <= 0:
                        raise Exception(f"商品 {oi_id} 的退貨數量必須大於 0")
                    
                    # 檢查累計退貨量
                    status_info = item_return_status.get(int(oi_id), {'original_qty': 0, 'returned_qty': 0})
                    if status_info['returned_qty'] + qty > status_info['original_qty']:
                        raise Exception(f"商品 {oi_id} 的累計退貨數量超過購買數量")

                    cursor.execute("""
                        INSERT INTO return_item (return_request_id, order_item_id, qty, reason, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, 'requested', %s, %s)
                    """, (return_request_id, oi_id, qty, reason, now, now))

                conn.commit()
                flash("退貨申請已送出，請靜候審核")
                return redirect(url_for('customer.customer_return.list_requests'))
            except Exception as e:
                conn.rollback()
                flash(f"申請失敗: {e}")

    # 獲取訂單商品明細，並合併已退貨狀態 (包含所有狀態，排除已拒絕的)
    cursor.execute("""
        SELECT oi.*, 
               COALESCE(SUM(CASE WHEN rr.status != 'rejected' THEN ri.qty ELSE 0 END), 0) as returned_qty
        FROM order_item oi
        LEFT JOIN return_item ri ON oi.id = ri.order_item_id
        LEFT JOIN return_request rr ON ri.return_request_id = rr.id
        WHERE oi.order_id = %s
        GROUP BY oi.id
    """, (order_id,))
    items = cursor.fetchall()
    
    # 計算剩餘可退數量
    for item in items:
        item['remaining_qty'] = item['qty'] - item['returned_qty']

    cursor.close()
    conn.close()
    return render_template('customer/return_apply.html', order=order, items=items)

@customer_return_bp.route('/list')
@login_required
def list_requests():
    customer_id = session['customer_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT rr.*, o.id as order_id, o.total as order_total
        FROM return_request rr
        JOIN orders o ON rr.order_id = o.id
        WHERE o.customer_id = %s
        ORDER BY rr.created_at DESC
    """, (customer_id,))
    returns = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('customer/return_list.html', returns=returns)

@customer_return_bp.route('/view/<int:id>')
@login_required
def view(id):
    customer_id = session['customer_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 檢查權限
    cursor.execute("""
        SELECT rr.*, o.id as order_id
        FROM return_request rr
        JOIN orders o ON rr.order_id = o.id
        WHERE rr.id = %s AND o.customer_id = %s
    """, (id, customer_id))
    return_req = cursor.fetchone()

    if not return_req:
        cursor.close()
        conn.close()
        flash("找不到該退貨紀錄")
        return redirect(url_for('customer.customer_return.list_requests'))

    # 獲取退貨項目
    cursor.execute("""
        SELECT ri.*, oi.product_name, oi.variant_name, oi.size, oi.color, oi.unit_price
        FROM return_item ri
        JOIN order_item oi ON ri.order_item_id = oi.id
        WHERE ri.return_request_id = %s
    """, (id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('customer/return_view.html', return_req=return_req, items=items)
