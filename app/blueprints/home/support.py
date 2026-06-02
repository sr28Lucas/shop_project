from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from datetime import datetime

support_bp = Blueprint('support', __name__)


def require_customer_login():
    return session.get('customer_id') is not None


def has_existing_refund_request(cursor, customer_id, order_id):
    """
    防呆：同一位顧客的同一筆訂單，只能申請一次退貨 / 退款。
    因為目前不改 SQL 結構，所以用 inquiry + message 內容中的訂單編號判斷。
    """
    cursor.execute("""
        SELECT i.id
        FROM inquiry i
        JOIN message m ON i.id = m.inquiry_id
        WHERE i.customer_id = %s
          AND i.purpose = '退貨退款'
          AND (
              m.content LIKE %s
              OR m.content LIKE %s
              OR m.content LIKE %s
              OR m.content LIKE %s
          )
        LIMIT 1
    """, (
        customer_id,
        f"%訂單編號：{order_id}%",
        f"%訂單編號:{order_id}%",
        f"%訂單 #{order_id}%",
        f"%訂單ID：{order_id}%"
    ))

    return cursor.fetchone() is not None


@support_bp.route('/new', methods=['GET', 'POST'])
def new_inquiry():
    if not require_customer_login():
        flash('請先登入會員')
        return redirect(url_for('auth.customer_login'))

    customer_id = session.get('customer_id')

    if request.method == 'POST':
        purpose = request.form.get('purpose', '').strip()
        content = request.form.get('content', '').strip()

        if not purpose:
            flash('請選擇問題類型')
            return redirect(url_for('home.support.new_inquiry'))

        if not content:
            flash('請輸入問題內容')
            return redirect(url_for('home.support.new_inquiry'))

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            now = datetime.now()

            cursor.execute("""
                INSERT INTO inquiry
                (customer_id, purpose, status, created_at, updated_at)
                VALUES (%s, %s, 'open', %s, %s)
            """, (customer_id, purpose, now, now))

            inquiry_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO message
                (inquiry_id, staff_id, customer_id, content, is_read, sent_at)
                VALUES (%s, NULL, %s, %s, 0, %s)
            """, (inquiry_id, customer_id, content, now))

            conn.commit()
            flash('客服問題已送出，請等待客服人員回覆')

            return redirect(url_for('home.support.detail', id=inquiry_id))

        except Exception as e:
            conn.rollback()
            flash(f'送出失敗：{e}')

        finally:
            cursor.close()
            conn.close()

    return render_template('home/support_new.html')


@support_bp.route('/list')
def list_inquiries():
    if not require_customer_login():
        flash('請先登入會員')
        return redirect(url_for('auth.customer_login'))

    customer_id = session.get('customer_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            i.id,
            i.purpose,
            i.status,
            i.created_at,
            i.updated_at,
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
                  AND m.staff_id IS NOT NULL
                  AND m.is_read = 0
            ) AS unread_count
        FROM inquiry i
        WHERE i.customer_id = %s
        ORDER BY 
            CASE WHEN i.status = 'closed' THEN 1 ELSE 0 END,
            COALESCE(i.updated_at, i.created_at) DESC
    """, (customer_id,))

    inquiries = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('home/support_list.html', inquiries=inquiries)


@support_bp.route('/detail/<int:id>')
def detail(id):
    if not require_customer_login():
        flash('請先登入會員')
        return redirect(url_for('auth.customer_login'))

    customer_id = session.get('customer_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM inquiry
        WHERE id = %s
          AND customer_id = %s
    """, (id, customer_id))

    inquiry = cursor.fetchone()

    if not inquiry:
        cursor.close()
        conn.close()
        flash('找不到客服案件')
        return redirect(url_for('home.support.list_inquiries'))

    cursor.execute("""
        SELECT
            m.*,
            s.name AS staff_name
        FROM message m
        LEFT JOIN staff s ON m.staff_id = s.id
        WHERE m.inquiry_id = %s
        ORDER BY m.sent_at ASC, m.id ASC
    """, (id,))

    messages = cursor.fetchall()

    # 會員打開案件後，把客服回覆標記為已讀
    cursor.execute("""
        UPDATE message
        SET is_read = 1
        WHERE inquiry_id = %s
          AND staff_id IS NOT NULL
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return render_template(
        'home/support_detail.html',
        inquiry=inquiry,
        messages=messages
    )


@support_bp.route('/reply/<int:id>', methods=['POST'])
def reply(id):
    if not require_customer_login():
        flash('請先登入會員')
        return redirect(url_for('auth.customer_login'))

    customer_id = session.get('customer_id')
    content = request.form.get('content', '').strip()

    if not content:
        flash('請輸入回覆內容')
        return redirect(url_for('home.support.detail', id=id))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT *
            FROM inquiry
            WHERE id = %s
              AND customer_id = %s
        """, (id, customer_id))

        inquiry = cursor.fetchone()

        if not inquiry:
            flash('找不到客服案件')
            return redirect(url_for('home.support.list_inquiries'))

        if inquiry['status'] == 'closed':
            flash('此案件已結案，無法繼續回覆')
            return redirect(url_for('home.support.detail', id=id))

        now = datetime.now()

        cursor.execute("""
            INSERT INTO message
            (inquiry_id, staff_id, customer_id, content, is_read, sent_at)
            VALUES (%s, NULL, %s, %s, 0, %s)
        """, (id, customer_id, content, now))

        cursor.execute("""
            UPDATE inquiry
            SET status = 'open',
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

    return redirect(url_for('home.support.detail', id=id))


@support_bp.route('/refund', methods=['GET', 'POST'])
def refund_request():
    if not require_customer_login():
        flash('請先登入會員')
        return redirect(url_for('auth.customer_login'))

    customer_id = session.get('customer_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        order_id = request.form.get('order_id', '').strip()
        reason = request.form.get('reason', '').strip()
        detail_text = request.form.get('detail', '').strip()

        if not order_id:
            flash('請選擇要申請退貨 / 退款的訂單')
            cursor.close()
            conn.close()
            return redirect(url_for('home.support.refund_request'))

        if not reason:
            flash('請選擇申請原因')
            cursor.close()
            conn.close()
            return redirect(url_for('home.support.refund_request'))

        if not detail_text:
            flash('請輸入詳細說明')
            cursor.close()
            conn.close()
            return redirect(url_for('home.support.refund_request'))

        try:
            cursor.execute("""
                SELECT id, total, status
                FROM orders
                WHERE id = %s
                  AND customer_id = %s
                LIMIT 1
            """, (order_id, customer_id))

            order = cursor.fetchone()

            if not order:
                flash('找不到此訂單，或此訂單不屬於目前會員')
                return redirect(url_for('home.support.refund_request'))

            # 防呆 1：已退款完成的訂單不能再次申請
            if order['status'] == 'refunded':
                flash(f'訂單 #{order_id} 已經完成退款，不能再次申請')
                return redirect(url_for('home.support.refund_request'))

            # 防呆 2：同一筆訂單只能申請一次退貨 / 退款
            if has_existing_refund_request(cursor, customer_id, order_id):
                flash(f'訂單 #{order_id} 已經申請過退貨 / 退款，不能重複申請')
                return redirect(url_for('home.support.refund_request'))

            if order['status'] not in ('shipped', 'completed'):
                flash('只有已出貨或已完成的訂單可以申請退貨 / 退款')
                return redirect(url_for('home.support.refund_request'))

            now = datetime.now()

            cursor.execute("""
                INSERT INTO inquiry
                (customer_id, purpose, status, created_at, updated_at)
                VALUES (%s, '退貨退款', 'open', %s, %s)
            """, (customer_id, now, now))

            inquiry_id = cursor.lastrowid

            content = f"""退貨 / 退款申請

訂單編號：{order_id}
訂單金額：{order['total']}
訂單狀態：{order['status']}
申請原因：{reason}

詳細說明：
{detail_text}
"""

            cursor.execute("""
                INSERT INTO message
                (inquiry_id, staff_id, customer_id, content, is_read, sent_at)
                VALUES (%s, NULL, %s, %s, 0, %s)
            """, (inquiry_id, customer_id, content, now))

            conn.commit()

            flash('退貨 / 退款申請已送出，請等待客服人員回覆')
            return redirect(url_for('home.support.detail', id=inquiry_id))

        except Exception as e:
            conn.rollback()
            flash(f'申請失敗：{e}')

        finally:
            cursor.close()
            conn.close()

    # GET：只顯示可以申請、而且還沒申請過的訂單
    cursor.execute("""
        SELECT 
            id,
            total,
            status,
            created_at
        FROM orders
        WHERE customer_id = %s
          AND status IN ('shipped', 'completed')
        ORDER BY created_at DESC
    """, (customer_id,))

    all_orders = cursor.fetchall()
    orders = []

    for order in all_orders:
        if not has_existing_refund_request(cursor, customer_id, order['id']):
            orders.append(order)

    cursor.close()
    conn.close()

    return render_template('home/refund_request.html', orders=orders)