from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from datetime import datetime

import re

inquiry_bp = Blueprint('inquiry', __name__)


def require_staff_login():
    return 'staff_id' in session


@inquiry_bp.route('/active')
def active_list():
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    keyword = request.args.get('keyword', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            i.id,
            i.customer_id,
            i.purpose,
            i.status,
            i.created_at,
            i.updated_at,
            c.name AS customer_name,
            c.email AS customer_email,
            c.phone AS customer_phone,
            (
                SELECT m.content
                FROM message m
                WHERE m.inquiry_id = i.id
                ORDER BY m.sent_at DESC, m.id DESC
                LIMIT 1
            ) AS last_message,
            (
                SELECT m.sent_at
                FROM message m
                WHERE m.inquiry_id = i.id
                ORDER BY m.sent_at DESC, m.id DESC
                LIMIT 1
            ) AS last_message_time,
            (
                SELECT COUNT(*)
                FROM message m
                WHERE m.inquiry_id = i.id
                  AND m.customer_id IS NOT NULL
                  AND m.is_read = 0
            ) AS unread_count
        FROM inquiry i
        JOIN customer c ON i.customer_id = c.id
        WHERE i.status != 'closed'
    """

    params = []

    if keyword:
        query += """
            AND (
                CAST(i.id AS CHAR) LIKE %s
                OR c.name LIKE %s
                OR c.email LIKE %s
                OR i.purpose LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    query += """
        ORDER BY
            CASE WHEN unread_count > 0 THEN 0 ELSE 1 END,
            COALESCE(last_message_time, i.updated_at, i.created_at) DESC
    """

    cursor.execute(query, params)
    inquiries = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'staff/inquiry_active.html',
        inquiries=inquiries,
        keyword=keyword
    )


@inquiry_bp.route('/history')
def history_list():
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    keyword = request.args.get('keyword', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            i.id,
            i.customer_id,
            i.purpose,
            i.status,
            i.created_at,
            i.updated_at,
            c.name AS customer_name,
            c.email AS customer_email,
            c.phone AS customer_phone,
            (
                SELECT m.content
                FROM message m
                WHERE m.inquiry_id = i.id
                ORDER BY m.sent_at DESC, m.id DESC
                LIMIT 1
            ) AS last_message,
            (
                SELECT m.sent_at
                FROM message m
                WHERE m.inquiry_id = i.id
                ORDER BY m.sent_at DESC, m.id DESC
                LIMIT 1
            ) AS last_message_time
        FROM inquiry i
        JOIN customer c ON i.customer_id = c.id
        WHERE i.status = 'closed'
    """

    params = []

    if keyword:
        query += """
            AND (
                CAST(i.id AS CHAR) LIKE %s
                OR c.name LIKE %s
                OR c.email LIKE %s
                OR i.purpose LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    query += """
        ORDER BY i.updated_at DESC, i.created_at DESC
    """

    cursor.execute(query, params)
    inquiries = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'staff/inquiry_history.html',
        inquiries=inquiries,
        keyword=keyword
    )


@inquiry_bp.route('/detail/<int:id>')
def detail(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            i.*,
            c.name AS customer_name,
            c.email AS customer_email,
            c.phone AS customer_phone
        FROM inquiry i
        JOIN customer c ON i.customer_id = c.id
        WHERE i.id = %s
    """, (id,))
    inquiry = cursor.fetchone()

    if not inquiry:
        cursor.close()
        conn.close()
        flash('找不到客服案件')
        return redirect(url_for('staff.inquiry.active_list'))

    cursor.execute("""
        SELECT
            m.*,
            c.name AS customer_name,
            s.name AS staff_name
        FROM message m
        LEFT JOIN customer c ON m.customer_id = c.id
        LEFT JOIN staff s ON m.staff_id = s.id
        WHERE m.inquiry_id = %s
        ORDER BY m.sent_at ASC, m.id ASC
    """, (id,))
    messages = cursor.fetchall()

    # 員工打開案件後，把客戶訊息標為已讀
    cursor.execute("""
        UPDATE message
        SET is_read = 1
        WHERE inquiry_id = %s
          AND customer_id IS NOT NULL
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return render_template(
        'staff/inquiry_detail.html',
        inquiry=inquiry,
        messages=messages
    )


@inquiry_bp.route('/reply/<int:id>', methods=['POST'])
def reply(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    content = request.form.get('content', '').strip()

    if not content:
        flash('回覆內容不可空白')
        return redirect(url_for('staff.inquiry.detail', id=id))

    staff_id = session.get('staff_id')
    now = datetime.now()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM inquiry WHERE id = %s", (id,))
        inquiry = cursor.fetchone()

        if not inquiry:
            flash('找不到客服案件')
            return redirect(url_for('staff.inquiry.active_list'))

        if inquiry['status'] == 'closed':
            flash('已結案案件不能直接回覆，請先重新開啟')
            return redirect(url_for('staff.inquiry.detail', id=id))

        cursor.execute("""
            INSERT INTO message
            (inquiry_id, staff_id, customer_id, content, is_read, sent_at)
            VALUES (%s, %s, NULL, %s, 0, %s)
        """, (id, staff_id, content, now))

        cursor.execute("""
            UPDATE inquiry
            SET status = 'replied',
                updated_at = %s
            WHERE id = %s
        """, (now, id))

        conn.commit()
        flash('已送出回覆')

    except Exception as e:
        conn.rollback()
        flash(f'回覆失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.inquiry.detail', id=id))


@inquiry_bp.route('/close/<int:id>', methods=['POST'])
def close(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    now = datetime.now()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE inquiry
            SET status = 'closed',
                updated_at = %s
            WHERE id = %s
        """, (now, id))

        conn.commit()
        flash('案件已結案，已移至客服歷史')

    except Exception as e:
        conn.rollback()
        flash(f'結案失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.inquiry.active_list'))


@inquiry_bp.route('/reopen/<int:id>', methods=['POST'])
def reopen(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    now = datetime.now()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE inquiry
            SET status = 'open',
                updated_at = %s
            WHERE id = %s
        """, (now, id))

        conn.commit()
        flash('案件已重新開啟')

    except Exception as e:
        conn.rollback()
        flash(f'重新開啟失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.inquiry.detail', id=id))

def extract_order_id_from_text(text):
    if not text:
        return None

    patterns = [
        r"訂單編號[:：]\s*(\d+)",
        r"訂單ID[:：]\s*(\d+)",
        r"訂單\s*#\s*(\d+)",
        r"訂單\s*(\d+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))

    return None


def get_refund_order_id(cursor, inquiry_id):
    cursor.execute("""
        SELECT content
        FROM message
        WHERE inquiry_id = %s
          AND customer_id IS NOT NULL
        ORDER BY sent_at ASC, id ASC
    """, (inquiry_id,))

    messages = cursor.fetchall()

    for msg in messages:
        order_id = extract_order_id_from_text(msg.get('content'))
        if order_id:
            return order_id

    return None


@inquiry_bp.route('/refund')
def refund_list():
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            i.id,
            i.customer_id,
            i.purpose,
            i.status,
            i.created_at,
            i.updated_at,
            c.name AS customer_name,
            c.email AS customer_email,
            c.phone AS customer_phone,
            (
                SELECT m.content
                FROM message m
                WHERE m.inquiry_id = i.id
                ORDER BY m.sent_at DESC, m.id DESC
                LIMIT 1
            ) AS last_message,
            (
                SELECT m.sent_at
                FROM message m
                WHERE m.inquiry_id = i.id
                ORDER BY m.sent_at DESC, m.id DESC
                LIMIT 1
            ) AS last_message_time
        FROM inquiry i
        JOIN customer c ON i.customer_id = c.id
        WHERE i.purpose = '退貨退款'
    """

    params = []

    if status:
        query += " AND i.status = %s "
        params.append(status)

    if keyword:
        query += """
            AND (
                CAST(i.id AS CHAR) LIKE %s
                OR c.name LIKE %s
                OR c.email LIKE %s
                OR c.phone LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    query += """
        ORDER BY
            CASE WHEN i.status = 'open' THEN 0
                 WHEN i.status = 'replied' THEN 1
                 ELSE 2 END,
            i.updated_at DESC,
            i.created_at DESC
    """

    cursor.execute(query, params)
    refunds = cursor.fetchall()

    for refund in refunds:
        refund['order_id'] = get_refund_order_id(cursor, refund['id'])

        if refund['order_id']:
            cursor.execute("""
                SELECT id, total, status, created_at
                FROM orders
                WHERE id = %s
            """, (refund['order_id'],))
            refund['order'] = cursor.fetchone()
        else:
            refund['order'] = None

    cursor.close()
    conn.close()

    return render_template(
        'staff/refund_list.html',
        refunds=refunds,
        keyword=keyword,
        status=status
    )


@inquiry_bp.route('/refund/approve/<int:id>', methods=['POST'])
def approve_refund(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    staff_id = session.get('staff_id')
    now = datetime.now()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT *
            FROM inquiry
            WHERE id = %s
              AND purpose = '退貨退款'
        """, (id,))
        inquiry = cursor.fetchone()

        if not inquiry:
            flash('找不到退貨 / 退款申請')
            return redirect(url_for('staff.inquiry.refund_list'))

        order_id = get_refund_order_id(cursor, id)

        if not order_id:
            flash('找不到申請內容中的訂單編號，請先查看案件內容')
            return redirect(url_for('staff.inquiry.refund_list'))

        cursor.execute("""
            SELECT id, status
            FROM orders
            WHERE id = %s
            LIMIT 1
        """, (order_id,))
        order = cursor.fetchone()

        if not order:
            flash('找不到對應訂單')
            return redirect(url_for('staff.inquiry.refund_list'))

        if order['status'] == 'refunded':
            flash('此訂單已經退款完成，不能再次審核')
            return redirect(url_for('staff.inquiry.refund_list'))

        cursor.execute("""
            SELECT id, status
            FROM payment
            WHERE order_id = %s
            LIMIT 1
        """, (order_id,))
        payment = cursor.fetchone()

        if payment and payment['status'] == 'refunded':
            flash('此訂單已經退款完成，不能再次審核')
            return redirect(url_for('staff.inquiry.refund_list'))

        # 將付款狀態改成 refund_processing，代表已通過審核但尚未完成退款
        if payment:
            cursor.execute("""
                UPDATE payment
                SET status = 'refund_processing'
                WHERE order_id = %s
            """, (order_id,))
        else:
            cursor.execute("""
                INSERT INTO payment
                (order_id, method, status, paid_at)
                VALUES (%s, 'unknown', 'refund_processing', NULL)
            """, (order_id,))

        cursor.execute("""
            INSERT INTO message
            (inquiry_id, staff_id, customer_id, content, is_read, sent_at)
            VALUES (%s, %s, NULL, %s, 0, %s)
        """, (
            id,
            staff_id,
            f"您的訂單 #{order_id} 退貨 / 退款申請已通過審核，客服將進一步處理退款流程。",
            now
        ))

        cursor.execute("""
            UPDATE inquiry
            SET status = 'replied',
                updated_at = %s
            WHERE id = %s
        """, (now, id))

        conn.commit()
        flash(f'訂單 #{order_id} 的退貨 / 退款申請已通過審核')

    except Exception as e:
        conn.rollback()
        flash(f'審核失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.inquiry.refund_list'))

@inquiry_bp.route('/refund/reject/<int:id>', methods=['POST'])
def reject_refund(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    staff_id = session.get('staff_id')
    reason = request.form.get('reason', '').strip()
    now = datetime.now()

    if not reason:
        reason = '經客服審核後，此申請未符合退貨 / 退款條件。'

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT *
            FROM inquiry
            WHERE id = %s
              AND purpose = '退貨退款'
        """, (id,))
        inquiry = cursor.fetchone()

        if not inquiry:
            flash('找不到退貨 / 退款申請')
            return redirect(url_for('staff.inquiry.refund_list'))

        cursor.execute("""
            INSERT INTO message
            (inquiry_id, staff_id, customer_id, content, is_read, sent_at)
            VALUES (%s, %s, NULL, %s, 0, %s)
        """, (
            id,
            staff_id,
            f"您的退貨 / 退款申請未通過審核。\n原因：{reason}",
            now
        ))

        cursor.execute("""
            UPDATE inquiry
            SET status = 'closed',
                updated_at = %s
            WHERE id = %s
        """, (now, id))

        conn.commit()
        flash('已拒絕退貨 / 退款申請，案件已結案')

    except Exception as e:
        conn.rollback()
        flash(f'拒絕申請失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.inquiry.refund_list'))


@inquiry_bp.route('/refund/complete/<int:id>', methods=['POST'])
def complete_refund(id):
    if not require_staff_login():
        return redirect(url_for('auth.staff_login'))

    staff_id = session.get('staff_id')
    now = datetime.now()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT *
            FROM inquiry
            WHERE id = %s
              AND purpose = '退貨退款'
        """, (id,))
        inquiry = cursor.fetchone()

        if not inquiry:
            flash('找不到退貨 / 退款申請')
            return redirect(url_for('staff.inquiry.refund_list'))

        order_id = get_refund_order_id(cursor, id)

        if not order_id:
            flash('找不到申請內容中的訂單編號')
            return redirect(url_for('staff.inquiry.refund_list'))

        cursor.execute("""
            SELECT id, status
            FROM orders
            WHERE id = %s
            LIMIT 1
        """, (order_id,))
        order = cursor.fetchone()

        if not order:
            flash('找不到對應訂單')
            return redirect(url_for('staff.inquiry.refund_list'))

        if order['status'] == 'refunded':
            flash('此訂單已經完成退款，不能重複退款')
            return redirect(url_for('staff.inquiry.refund_list'))

        # 防呆 1：必須先通過審核
        cursor.execute("""
            SELECT status
            FROM payment
            WHERE order_id = %s
            LIMIT 1
        """, (order_id,))
        payment = cursor.fetchone()

        if not payment or payment['status'] != 'refund_processing':
            flash('此申請尚未通過審核，請先點擊「通過審核」後才能完成退款')
            return redirect(url_for('staff.inquiry.refund_list'))

        # 退貨入庫：把商品庫存加回去
        cursor.execute("""
            SELECT sku_id, qty
            FROM order_item
            WHERE order_id = %s
              AND sku_id IS NOT NULL
        """, (order_id,))
        items = cursor.fetchall()

        for item in items:
            cursor.execute("""
                UPDATE sku
                SET stock = stock + %s,
                    updated_at = %s
                WHERE id = %s
            """, (item['qty'], now, item['sku_id']))

        # 訂單改為 refunded
        cursor.execute("""
            UPDATE orders
            SET status = 'refunded',
                updated_at = %s
            WHERE id = %s
        """, (now, order_id))

        # 付款改為 refunded
        cursor.execute("""
            UPDATE payment
            SET status = 'refunded'
            WHERE order_id = %s
        """, (order_id,))

        # 物流改為 returned
        cursor.execute("""
            SELECT id
            FROM shipment
            WHERE order_id = %s
            LIMIT 1
        """, (order_id,))
        shipment = cursor.fetchone()

        if shipment:
            cursor.execute("""
                UPDATE shipment
                SET status = 'returned',
                    delivered_at = %s
                WHERE order_id = %s
            """, (now, order_id))
        else:
            cursor.execute("""
                INSERT INTO shipment
                (order_id, status, shipped_at, delivered_at)
                VALUES (%s, 'returned', NULL, %s)
            """, (order_id, now))

        cursor.execute("""
            INSERT INTO message
            (inquiry_id, staff_id, customer_id, content, is_read, sent_at)
            VALUES (%s, %s, NULL, %s, 0, %s)
        """, (
            id,
            staff_id,
            f"訂單 #{order_id} 已完成退貨 / 退款處理，退款狀態已更新，退貨商品庫存已回補。",
            now
        ))

        cursor.execute("""
            UPDATE inquiry
            SET status = 'closed',
                updated_at = %s
            WHERE id = %s
        """, (now, id))

        conn.commit()
        flash(f'訂單 #{order_id} 已完成退貨 / 退款，案件已結案')

    except Exception as e:
        conn.rollback()
        flash(f'完成退款失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.inquiry.refund_list'))