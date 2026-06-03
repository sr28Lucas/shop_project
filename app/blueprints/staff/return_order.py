from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from datetime import datetime
from .permission import require_permission

staff_return_bp = Blueprint('staff_return', __name__)

@staff_return_bp.route('/list')
@require_permission('return')
def list_requests():
    status_filter = request.args.get('status', '').strip()
    keyword = request.args.get('keyword', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT rr.*, o.id as order_id, c.name as customer_name, c.email as customer_email
        FROM return_request rr
        JOIN orders o ON rr.order_id = o.id
        JOIN customer c ON o.customer_id = c.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND rr.status = %s"
        params.append(status_filter)
    
    if keyword:
        query += " AND (CAST(rr.id AS CHAR) LIKE %s OR CAST(o.id AS CHAR) LIKE %s OR c.name LIKE %s OR c.email LIKE %s)"
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    query += " ORDER BY rr.created_at DESC"

    cursor.execute(query, params)
    returns = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('staff/return_list.html', returns=returns, status_filter=status_filter, keyword=keyword)

@staff_return_bp.route('/detail/<int:id>')
@require_permission('return')
def detail(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT rr.*, o.id as order_id, o.total as order_total, c.name as customer_name, c.phone as customer_phone
        FROM return_request rr
        JOIN orders o ON rr.order_id = o.id
        JOIN customer c ON o.customer_id = c.id
        WHERE rr.id = %s
    """, (id,))
    return_req = cursor.fetchone()

    if not return_req:
        cursor.close()
        conn.close()
        flash("找不到該退貨申請")
        return redirect(url_for('staff.staff_return.list_requests'))

    cursor.execute("""
        SELECT ri.*, oi.product_name, oi.variant_name, oi.size, oi.color, oi.unit_price, oi.sku_id
        FROM return_item ri
        JOIN order_item oi ON ri.order_item_id = oi.id
        WHERE ri.return_request_id = %s
    """, (id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('staff/return_detail.html', return_req=return_req, items=items)

@staff_return_bp.route('/approve/<int:id>', methods=['POST'])
@require_permission('return')
def approve(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE return_request SET status = 'approved', approved_at = %s, updated_at = %s WHERE id = %s",
                       (datetime.now(), datetime.now(), id))
        conn.commit()
        flash(f"退貨申請 #{id} 已核准")
    except Exception as e:
        conn.rollback()
        flash(f"核准失敗: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.staff_return.detail', id=id))

@staff_return_bp.route('/reject/<int:id>', methods=['POST'])
@require_permission('return')
def reject(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE return_request SET status = 'rejected', rejected_at = %s, updated_at = %s WHERE id = %s",
                       (datetime.now(), datetime.now(), id))
        conn.commit()
        flash(f"退貨申請 #{id} 已拒絕")
    except Exception as e:
        conn.rollback()
        flash(f"拒絕失敗: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.staff_return.detail', id=id))

@staff_return_bp.route('/complete/<int:id>', methods=['POST'])
@require_permission('return')
def complete(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 獲取申請資訊
        cursor.execute("SELECT order_id, status FROM return_request WHERE id = %s FOR UPDATE", (id,))
        ret = cursor.fetchone()
        if not ret or ret['status'] == 'refunded' or ret['status'] == 'rejected':
            flash("申請不存在，或處於無法退款的狀態 (已退款或已被拒絕)")
            return redirect(url_for('staff.staff_return.list_requests'))

        order_id = ret['order_id']
        now = datetime.now()

        # 2. 獲取訂單總額
        cursor.execute("SELECT total FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        order_total = order['total']

        # 3. 計算本次退貨金額與回補庫存
        cursor.execute("""
            SELECT ri.qty, oi.sku_id, oi.unit_price
            FROM return_item ri
            JOIN order_item oi ON ri.order_item_id = oi.id
            WHERE ri.return_request_id = %s
            FOR UPDATE
        """, (id,))
        items = cursor.fetchall()

        current_refund_amount = 0
        for item in items:
            current_refund_amount += (item['qty'] * item['unit_price'])
            if item['sku_id']:
                cursor.execute("UPDATE sku SET stock = stock + %s, updated_at = %s WHERE id = %s",
                               (item['qty'], now, item['sku_id']))

        # 4. 計算該訂單已退款總額 (包含本次)
        cursor.execute("""
            SELECT SUM(ri.qty * oi.unit_price) as total_refunded
            FROM return_request rr
            JOIN return_item ri ON rr.id = ri.return_request_id
            JOIN order_item oi ON ri.order_item_id = oi.id
            WHERE rr.order_id = %s AND rr.status = 'refunded'
        """, (order_id,))
        previous_refunded = cursor.fetchone()['total_refunded'] or 0
        total_refunded = previous_refunded + current_refund_amount

        # 5. 更新狀態
        cursor.execute("UPDATE return_request SET status = 'refunded', refunded_at = %s, updated_at = %s WHERE id = %s",
                       (now, now, id))
        
        # 只有在已退款總額達到或超過訂單總額時，才將訂單標記為 'refunded'
        if total_refunded >= order_total:
            cursor.execute("UPDATE orders SET status = 'refunded', updated_at = %s WHERE id = %s", (now, order_id))
            cursor.execute("UPDATE payment SET status = 'refunded' WHERE order_id = %s", (order_id,))

        conn.commit()
        flash(f"退貨申請 #{id} 已完成退款並回補庫存 (本次退款: ${current_refund_amount:.0f})")
    except Exception as e:
        conn.rollback()
        flash(f"操作失敗: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.staff_return.detail', id=id))
