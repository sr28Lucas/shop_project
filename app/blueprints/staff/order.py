from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import get_db_connection
from datetime import datetime
import json
import os
from app.config import config
from .permission import require_permission

order_bp = Blueprint('order', __name__)


@order_bp.route('/logistics_settings', methods=['GET', 'POST'])
@require_permission('orders')
def logistics_settings():
    json_path = os.path.join(config.BASE_DIR, 'app', 'static', 'json', 'taiwan_districts.json')

    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for city in data:
                fee = request.form.get(f'fee_{city}')
                if fee:
                    data[city]['fee'] = float(fee)
                    cursor.execute(
                        "UPDATE region SET fee = %s WHERE name = %s",
                        (float(fee), city)
                    )

            conn.commit()

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            flash('運費設定已更新')

        except Exception as e:
            conn.rollback()
            flash(f'運費設定更新失敗：{e}')

        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('staff.order.logistics_settings'))

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return render_template('staff/logistics_settings.html', data=data)


@order_bp.route('/list')
@require_permission('orders')
def order_list():
    """
    出貨管理只顯示未出貨訂單。
    確認出貨或取消後，訂單會從這裡消失。
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            o.*,
            c.name AS customer_name,
            COALESCE(s.status, 'pending') AS shipment_status
        FROM orders o
        LEFT JOIN customer c ON o.customer_id = c.id
        LEFT JOIN shipment s ON o.id = s.order_id
        WHERE 
            o.status = 'pending'
            AND COALESCE(s.status, 'pending') = 'pending'
        ORDER BY o.created_at DESC
    """

    cursor.execute(query)
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('staff/order_list.html', orders=orders)


@order_bp.route('/history')
@require_permission('orders')
def order_history():
    """
    訂單歷史顯示：
    shipped：已出貨
    completed：已完成
    cancelled：已取消
    """
    keyword = request.args.get('keyword', '').strip()
    status_filter = request.args.get('status', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            o.*,
            c.name AS customer_name,
            COALESCE(s.status, '-') AS shipment_status
        FROM orders o
        LEFT JOIN customer c ON o.customer_id = c.id
        LEFT JOIN shipment s ON o.id = s.order_id
        WHERE 
            (
                o.status IN ('shipped', 'completed', 'cancelled')
                OR COALESCE(s.status, '') IN ('shipped', 'delivered', 'cancelled')
            )
    """

    params = []

    if status_filter == 'shipped':
        query += """
            AND (
                o.status = 'shipped'
                OR COALESCE(s.status, '') = 'shipped'
            )
        """
    elif status_filter == 'cancelled':
        query += """
            AND (
                o.status = 'cancelled'
                OR COALESCE(s.status, '') = 'cancelled'
            )
        """
    elif status_filter == 'completed':
        query += """
            AND (
                o.status = 'completed'
                OR COALESCE(s.status, '') = 'delivered'
            )
        """

    if keyword:
        query += """
            AND (
                CAST(o.id AS CHAR) LIKE %s
                OR c.name LIKE %s
                OR o.name LIKE %s
                OR o.phone LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])

    query += " ORDER BY o.created_at DESC"

    cursor.execute(query, params)
    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'staff/order_history.html',
        orders=orders,
        keyword=keyword,
        status_filter=status_filter
    )


@order_bp.route('/ship/<int:id>', methods=['POST'])
@require_permission('orders')
def ship_order(id):
    """
    確認出貨：
    orders.status = shipped
    shipment.status = shipped
    然後訂單會從出貨管理消失，進入訂單歷史。
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        now = datetime.now()

        cursor.execute("""
            SELECT 
                o.id,
                o.status,
                COALESCE(s.status, 'pending') AS shipment_status
            FROM orders o
            LEFT JOIN shipment s ON o.id = s.order_id
            WHERE o.id = %s
            LIMIT 1
        """, (id,))
        order = cursor.fetchone()

        if not order:
            flash('找不到訂單')
            return redirect(url_for('staff.order.order_list'))

        if order['status'] == 'cancelled':
            flash('已取消訂單不能出貨')
            return redirect(url_for('staff.order.order_list'))

        if order['status'] != 'pending':
            flash('此訂單不是待出貨狀態')
            return redirect(url_for('staff.order.order_list'))

        cursor.execute("SELECT id FROM shipment WHERE order_id = %s LIMIT 1", (id,))
        shipment = cursor.fetchone()

        if shipment:
            cursor.execute("""
                UPDATE shipment
                SET status = 'shipped',
                    shipped_at = %s,
                    delivered_at = NULL
                WHERE order_id = %s
            """, (now, id))
        else:
            cursor.execute("""
                INSERT INTO shipment
                (order_id, status, shipped_at, delivered_at)
                VALUES (%s, 'shipped', %s, NULL)
            """, (id, now))

        cursor.execute("""
            UPDATE orders
            SET status = 'shipped',
                updated_at = %s
            WHERE id = %s
        """, (now, id))

        conn.commit()
        flash(f'訂單 {id} 已確認出貨，已移至訂單歷史')

    except Exception as e:
        conn.rollback()
        flash(f'確認出貨失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.order.order_list'))


@order_bp.route('/cancel/<int:id>', methods=['POST'])
@require_permission('orders')
def cancel_order(id):
    """
    取消訂單：
    orders.status = cancelled
    shipment.status = cancelled
    sku.stock 加回去
    然後訂單會從出貨管理消失，進入訂單歷史。
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        now = datetime.now()

        cursor.execute("""
            SELECT 
                o.id,
                o.status,
                COALESCE(s.status, 'pending') AS shipment_status
            FROM orders o
            LEFT JOIN shipment s ON o.id = s.order_id
            WHERE o.id = %s
            LIMIT 1
        """, (id,))
        order = cursor.fetchone()

        if not order:
            flash('找不到訂單')
            return redirect(url_for('staff.order.order_list'))

        if order['status'] == 'cancelled':
            flash('此訂單已經取消過')
            return redirect(url_for('staff.order.order_list'))

        if order['status'] != 'pending':
            flash('只有未出貨訂單可以取消')
            return redirect(url_for('staff.order.order_list'))

        cursor.execute("""
            SELECT sku_id, qty
            FROM order_item
            WHERE order_id = %s
              AND sku_id IS NOT NULL
        """, (id,))
        items = cursor.fetchall()

        for item in items:
            cursor.execute("""
                UPDATE sku
                SET stock = stock + %s,
                    updated_at = %s
                WHERE id = %s
            """, (item['qty'], now, item['sku_id']))

        cursor.execute("""
            UPDATE orders
            SET status = 'cancelled',
                updated_at = %s
            WHERE id = %s
        """, (now, id))

        cursor.execute("SELECT id FROM shipment WHERE order_id = %s LIMIT 1", (id,))
        shipment = cursor.fetchone()

        if shipment:
            cursor.execute("""
                UPDATE shipment
                SET status = 'cancelled',
                    shipped_at = NULL,
                    delivered_at = NULL
                WHERE order_id = %s
            """, (id,))
        else:
            cursor.execute("""
                INSERT INTO shipment
                (order_id, status, shipped_at, delivered_at)
                VALUES (%s, 'cancelled', NULL, NULL)
            """, (id,))

        cursor.execute("""
            UPDATE payment
            SET status = CASE
                WHEN status = 'paid' THEN 'refunded'
                ELSE 'cancelled'
            END
            WHERE order_id = %s
        """, (id,))

        conn.commit()
        flash(f'訂單 {id} 已取消，庫存已恢復，已移至訂單歷史')

    except Exception as e:
        conn.rollback()
        flash(f'取消訂單失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.order.order_list'))


@order_bp.route('/deliver/<int:id>', methods=['POST'])
@require_permission('orders')
def deliver_order(id):
    """
    訂單歷史裡可以把 shipped 改成 completed。
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        now = datetime.now()

        cursor.execute("""
            SELECT 
                o.id,
                o.status,
                COALESCE(s.status, 'pending') AS shipment_status
            FROM orders o
            LEFT JOIN shipment s ON o.id = s.order_id
            WHERE o.id = %s
            LIMIT 1
        """, (id,))
        order = cursor.fetchone()

        if not order:
            flash('找不到訂單')
            return redirect(url_for('staff.order.order_history'))

        if order['status'] == 'cancelled':
            flash('已取消訂單不能完成送達')
            return redirect(url_for('staff.order.order_history'))

        cursor.execute("SELECT id FROM shipment WHERE order_id = %s LIMIT 1", (id,))
        shipment = cursor.fetchone()

        if shipment:
            cursor.execute("""
                UPDATE shipment
                SET status = 'delivered',
                    delivered_at = %s
                WHERE order_id = %s
            """, (now, id))
        else:
            cursor.execute("""
                INSERT INTO shipment
                (order_id, status, shipped_at, delivered_at)
                VALUES (%s, 'delivered', %s, %s)
            """, (id, now, now))

        cursor.execute("""
            UPDATE orders
            SET status = 'completed',
                updated_at = %s
            WHERE id = %s
        """, (now, id))
        conn.commit()
        flash(f'訂單 {id} 已完成送達')

    except Exception as e:
        conn.rollback()
        flash(f'完成送達失敗：{e}')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('staff.order.order_history'))


@order_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@require_permission('orders')
def order_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        item_id = request.form.get('item_id')

        if item_id:
            try:
                cursor.execute("""
                    SELECT sku_id, qty
                    FROM order_item
                    WHERE id = %s AND order_id = %s
                """, (item_id, id))
                item = cursor.fetchone()

                if item and item['sku_id']:
                    cursor.execute("""
                        UPDATE sku
                        SET stock = stock + %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (item['qty'], item['sku_id']))

                cursor.execute("""
                    DELETE FROM order_item
                    WHERE id = %s AND order_id = %s
                """, (item_id, id))

                conn.commit()
                flash('已移除訂單項目，庫存已恢復')

            except Exception as e:
                conn.rollback()
                flash(f'移除失敗：{e}')

            finally:
                cursor.close()
                conn.close()

            return redirect(url_for('staff.order.order_edit', id=id))

    cursor.execute("""
        SELECT 
            o.*,
            c.name AS customer_name,
            COALESCE(s.status, 'pending') AS shipment_status
        FROM orders o
        LEFT JOIN customer c ON o.customer_id = c.id
        LEFT JOIN shipment s ON o.id = s.order_id
        WHERE o.id = %s
        LIMIT 1
    """, (id,))
    order = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM order_item
        WHERE order_id = %s
    """, (id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('staff/order_edit.html', order=order, items=items)

@order_bp.route('/detail/<int:id>')
@require_permission('orders')
def order_detail(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            o.*,
            c.name AS customer_name,
            COALESCE(s.status, 'pending') AS shipment_status
        FROM orders o
        LEFT JOIN customer c ON o.customer_id = c.id
        LEFT JOIN shipment s ON o.id = s.order_id
        WHERE o.id = %s
        LIMIT 1
    """, (id,))
    order = cursor.fetchone()

    # 獲取訂單項目，並計算已退貨數量 (僅統計狀態為 'refunded' 的項目)
    cursor.execute("""
        SELECT oi.*, 
               COALESCE(SUM(CASE WHEN rr.status = 'refunded' THEN ri.qty ELSE 0 END), 0) as returned_qty
        FROM order_item oi
        LEFT JOIN return_item ri ON oi.id = ri.order_item_id
        LEFT JOIN return_request rr ON ri.return_request_id = rr.id
        WHERE oi.order_id = %s
        GROUP BY oi.id
    """, (id,))
    items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('staff/order_detail.html', order=order, items=items)