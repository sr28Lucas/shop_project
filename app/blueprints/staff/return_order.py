from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from datetime import datetime

staff_return_bp = Blueprint('staff_return', __name__)

def require_staff_login():
    return 'staff_id' in session

@staff_return_bp.route('/list')
def list_requests():
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

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
def detail(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

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
def approve(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

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
def reject(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

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
def complete(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 獲取申請資訊
        cursor.execute("SELECT order_id, status FROM return_request WHERE id = %s", (id,))
        ret = cursor.fetchone()
        if not ret or ret['status'] == 'refunded':
            flash("申請不存在或已完成退款")
            return redirect(url_for('staff.staff_return.list_requests'))

        order_id = ret['order_id']
        now = datetime.now()

        # 2. 獲取退貨項目以回補庫存
        cursor.execute("""
            SELECT ri.qty, oi.sku_id
            FROM return_item ri
            JOIN order_item oi ON ri.order_item_id = oi.id
            WHERE ri.return_request_id = %s
        """, (id,))
        items = cursor.fetchall()

        for item in items:
            if item['sku_id']:
                cursor.execute("UPDATE sku SET stock = stock + %s, updated_at = %s WHERE id = %s",
                               (item['qty'], now, item['sku_id']))

        # 3. 更新狀態
        cursor.execute("UPDATE return_request SET status = 'refunded', refunded_at = %s, updated_at = %s WHERE id = %s",
                       (now, now, id))
        
        # 更新訂單狀態為已退款 (部分退款邏輯此處簡化為標記訂單)
        cursor.execute("UPDATE orders SET status = 'refunded', updated_at = %s WHERE id = %s", (now, order_id))
        
        # 更新付款狀態
        cursor.execute("UPDATE payment SET status = 'refunded' WHERE order_id = %s", (order_id,))

        conn.commit()
        flash(f"退貨申請 #{id} 已完成退款並回補庫存")
    except Exception as e:
        conn.rollback()
        flash(f"操作失敗: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.staff_return.detail', id=id))
