from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from datetime import datetime
from .permission import require_permission

member_bp = Blueprint('member', __name__)


@member_bp.route('/list')
@require_permission('member')
def member_list():
    keyword = request.args.get('keyword', '').strip()
    status = request.args.get('status', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            c.id,
            c.name,
            c.email,
            c.phone,
            c.is_active,
            c.created_at,
            c.updated_at,

            (
                SELECT COUNT(*)
                FROM orders o
                WHERE o.customer_id = c.id
            ) AS order_count,

            (
                SELECT COALESCE(SUM(o.total), 0)
                FROM orders o
                WHERE o.customer_id = c.id
                  AND o.status IN ('shipped', 'completed')
            ) AS total_spent,

            (
                SELECT COUNT(*)
                FROM inquiry i
                WHERE i.customer_id = c.id
            ) AS inquiry_count

        FROM customer c
        WHERE 1 = 1
    """

    params = []

    if keyword:
        query += """
            AND (
                c.name LIKE %s
                OR c.email LIKE %s
                OR c.phone LIKE %s
                OR CAST(c.id AS CHAR) LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    if status == 'active':
        query += " AND c.is_active = 1 "
    elif status == 'inactive':
        query += " AND c.is_active = 0 "

    query += """
        ORDER BY c.created_at DESC, c.id DESC
    """

    cursor.execute(query, params)
    members = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'staff/member_list.html',
        members=members,
        keyword=keyword,
        status=status
    )


@member_bp.route('/detail/<int:id>')
@require_permission('member')
def member_detail(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            phone,
            is_active,
            created_at,
            updated_at
        FROM customer
        WHERE id = %s
        LIMIT 1
    """, (id,))

    member = cursor.fetchone()

    if not member:
        cursor.close()
        conn.close()
        flash('找不到會員資料')
        return redirect(url_for('staff.member.member_list'))

    cursor.execute("""
        SELECT
            id,
            status,
            total,
            name,
            phone,
            region,
            locality,
            address,
            created_at,
            updated_at
        FROM orders
        WHERE customer_id = %s
        ORDER BY created_at DESC
        LIMIT 20
    """, (id,))

    orders = cursor.fetchall()

    cursor.execute("""
        SELECT
            id,
            purpose,
            status,
            created_at,
            updated_at
        FROM inquiry
        WHERE customer_id = %s
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 20
    """, (id,))

    inquiries = cursor.fetchall()

    cursor.execute("""
        SELECT
            COUNT(*) AS order_count,
            COALESCE(SUM(CASE WHEN status IN ('shipped', 'completed') THEN total ELSE 0 END), 0) AS total_spent,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) AS pending_count,
            COUNT(CASE WHEN status = 'cancelled' THEN 1 END) AS cancelled_count,
            COUNT(CASE WHEN status = 'refunded' THEN 1 END) AS refunded_count
        FROM orders
        WHERE customer_id = %s
    """, (id,))

    summary = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'staff/member_detail.html',
        member=member,
        orders=orders,
        inquiries=inquiries,
        summary=summary
    )


@member_bp.route('/toggle/<int:id>', methods=['POST'])
@require_permission('member')
def toggle_member(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, name, is_active
            FROM customer
            WHERE id = %s
            LIMIT 1
        """, (id,))

        member = cursor.fetchone()

        if not member:
            flash('找不到會員資料')
            return redirect(url_for('staff.member.member_list'))

        new_status = 0 if member['is_active'] else 1

        cursor.execute("""
            UPDATE customer
            SET is_active = %s,
                updated_at = %s
            WHERE id = %s
        """, (new_status, datetime.now(), id))

        conn.commit()

        if new_status == 1:
            flash(f"會員「{member['name']}」已啟用")
        else:
            flash(f"會員「{member['name']}」已停用")

    except Exception as e:
        conn.rollback()
        flash(f'更新會員狀態失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.member.member_list'))