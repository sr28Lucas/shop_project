from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from datetime import datetime
from app.utils.validators import Validator

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

        if not purpose or not content:
            flash("請填寫所有欄位")
            return redirect(url_for('home.support.new_inquiry'))

        if not Validator.is_valid_length(purpose, 100, 1):
            flash("諮詢主題長度需在 1-100 字元之間")
            return redirect(url_for('home.support.new_inquiry'))

        if not Validator.is_valid_length(content, 2000, 1):
            flash("諮詢內容長度需在 1-2000 字元之間")
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
    flash("退貨申請系統已更新，請從您的『歷史訂單』中選擇欲退貨的訂單進行申請。")
    return redirect(url_for('customer.customer_order.order_list'))