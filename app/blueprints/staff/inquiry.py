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