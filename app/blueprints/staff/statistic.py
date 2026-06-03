from flask import Blueprint, render_template, request
from app.db import get_db_connection
from datetime import date
from .permission import require_permission

statistic_bp = Blueprint('statistic', __name__)


def get_date_range():
    today = date.today()
    first_day = today.replace(day=1)

    start_date = request.args.get('start_date') or first_day.strftime('%Y-%m-%d')
    end_date = request.args.get('end_date') or today.strftime('%Y-%m-%d')

    return start_date, end_date


@statistic_bp.route('/')
@require_permission('statistic')
def index():
    return revenue()


@statistic_bp.route('/revenue')
@require_permission('statistic')
def revenue():
    start_date, end_date = get_date_range()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. 基礎 KPI (修正: 使用 order_item 與 return_item 計算淨營收)
    cursor.execute("""
        SELECT
            COALESCE(SUM(oi.qty * oi.unit_price), 0) - COALESCE(SUM(ri.qty * oi.unit_price), 0) AS net_revenue,
            COUNT(DISTINCT o.id) AS revenue_order_count
        FROM orders o
        JOIN order_item oi ON o.id = oi.order_id
        LEFT JOIN return_item ri ON oi.id = ri.order_item_id
        LEFT JOIN return_request rr ON ri.return_request_id = rr.id AND rr.status = 'refunded'
        WHERE DATE(o.created_at) BETWEEN %s AND %s
          AND o.status IN ('shipped', 'completed', 'refunded')
    """, (start_date, end_date))
    kpi_net = cursor.fetchone()

    # 為了維持現有統計頁面需要的其他數量統計，保留原始 status 統計查詢
    cursor.execute("""
        SELECT
            COUNT(CASE WHEN o.status = 'pending' THEN 1 END) AS pending_order_count,
            COUNT(CASE WHEN o.status = 'cancelled' THEN 1 END) AS cancelled_order_count,
            COUNT(CASE WHEN o.status = 'refunded' OR EXISTS (SELECT 1 FROM return_request rr WHERE rr.order_id = o.id AND rr.status = 'refunded') THEN 1 END) AS refunded_order_count,
            COUNT(*) AS all_order_count
        FROM orders o
        WHERE DATE(o.created_at) BETWEEN %s AND %s
    """, (start_date, end_date))
    order_counts = cursor.fetchone()
    
    kpi = {**kpi_net, **order_counts}

    total_revenue = float(kpi['net_revenue'] or 0)
    revenue_order_count = int(kpi['revenue_order_count'] or 0)
    avg_order_value = round(total_revenue / revenue_order_count, 2) if revenue_order_count > 0 else 0

    cursor.execute("""
        SELECT
            DATE_FORMAT(o.created_at, '%Y-%m-%d') AS order_date,
            COUNT(*) AS order_count,
            COALESCE(SUM(o.total), 0) AS daily_revenue
        FROM orders o
        WHERE DATE(o.created_at) BETWEEN %s AND %s
          AND o.status IN ('shipped', 'completed')
        GROUP BY DATE(o.created_at)
        ORDER BY DATE(o.created_at)
    """, (start_date, end_date))
    daily_revenue = cursor.fetchall()

    cursor.execute("""
        SELECT
            o.status,
            COUNT(*) AS count
        FROM orders o
        WHERE DATE(o.created_at) BETWEEN %s AND %s
        GROUP BY o.status
        ORDER BY count DESC
    """, (start_date, end_date))
    status_summary = cursor.fetchall()

    cursor.execute("""
        SELECT
            COALESCE(c.name, '未分類') AS category_name,
            COALESCE(SUM(oi.qty), 0) AS total_qty,
            COALESCE(SUM(oi.qty * oi.unit_price), 0) AS total_revenue
        FROM order_item oi
        JOIN orders o ON oi.order_id = o.id
        LEFT JOIN product p ON oi.product_id = p.id
        LEFT JOIN category c ON p.category_id = c.id
        WHERE DATE(o.created_at) BETWEEN %s AND %s
          AND o.status IN ('shipped', 'completed')
        GROUP BY c.name
        ORDER BY total_revenue DESC
    """, (start_date, end_date))
    category_revenue = cursor.fetchall()

    cursor.execute("""
        SELECT
            oi.product_name,
            COALESCE(SUM(oi.qty), 0) AS total_qty,
            COALESCE(SUM(oi.qty * oi.unit_price), 0) AS total_revenue
        FROM order_item oi
        JOIN orders o ON oi.order_id = o.id
        WHERE DATE(o.created_at) BETWEEN %s AND %s
          AND o.status IN ('shipped', 'completed')
        GROUP BY oi.product_name
        ORDER BY total_revenue DESC
        LIMIT 10
    """, (start_date, end_date))
    top_products = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'staff/statistic_revenue.html',
        start_date=start_date,
        end_date=end_date,
        kpi=kpi,
        total_revenue=total_revenue,
        avg_order_value=avg_order_value,
        daily_revenue=daily_revenue,
        status_summary=status_summary,
        category_revenue=category_revenue,
        top_products=top_products
    )


@statistic_bp.route('/sales')
@require_permission('statistic')
def sales():
    start_date, end_date = get_date_range()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. 暢銷商品分析 (修正: 扣除退貨)
    cursor.execute("""
        SELECT
            oi.product_name,
            oi.color,
            oi.size,
            COALESCE(SUM(oi.qty), 0) - COALESCE(SUM(ri.qty), 0) AS total_qty,
            COALESCE(SUM(oi.qty * oi.unit_price), 0) - COALESCE(SUM(ri.qty * oi.unit_price), 0) AS total_revenue,
            ROUND(
                (COALESCE(SUM(oi.qty * oi.unit_price), 0) - COALESCE(SUM(ri.qty * oi.unit_price), 0)) / 
                NULLIF(COALESCE(SUM(oi.qty), 0) - COALESCE(SUM(ri.qty), 0), 0),
                2
            ) AS avg_price
        FROM order_item oi
        JOIN orders o ON oi.order_id = o.id
        LEFT JOIN return_item ri ON oi.id = ri.order_item_id
        LEFT JOIN return_request rr ON ri.return_request_id = rr.id AND rr.status = 'refunded'
        WHERE DATE(o.created_at) BETWEEN %s AND %s
          AND o.status IN ('shipped', 'completed', 'refunded')
        GROUP BY oi.product_name, oi.color, oi.size
        ORDER BY total_qty DESC, total_revenue DESC
        LIMIT 50
    """, (start_date, end_date))
    product_sales = cursor.fetchall()

    # 2. 分類銷售分析 (修正: 扣除退貨)
    cursor.execute("""
        SELECT
            COALESCE(c.name, '未分類') AS category_name,
            COALESCE(SUM(oi.qty), 0) - COALESCE(SUM(ri.qty), 0) AS total_qty,
            COALESCE(SUM(oi.qty * oi.unit_price), 0) - COALESCE(SUM(ri.qty * oi.unit_price), 0) AS total_revenue
        FROM order_item oi
        JOIN orders o ON oi.order_id = o.id
        LEFT JOIN product p ON oi.product_id = p.id
        LEFT JOIN category c ON p.category_id = c.id
        LEFT JOIN return_item ri ON oi.id = ri.order_item_id
        LEFT JOIN return_request rr ON ri.return_request_id = rr.id AND rr.status = 'refunded'
        WHERE DATE(o.created_at) BETWEEN %s AND %s
          AND o.status IN ('shipped', 'completed', 'refunded')
        GROUP BY c.name
        ORDER BY total_qty DESC
    """, (start_date, end_date))
    category_sales = cursor.fetchall()

    # 3. 庫存 KPI (保持不變)
    cursor.execute("""
        SELECT
            COUNT(*) AS sku_count,
            COALESCE(SUM(stock), 0) AS total_stock,
            COUNT(CASE WHEN stock <= 5 THEN 1 END) AS low_stock_count,
            COUNT(CASE WHEN stock = 0 THEN 1 END) AS out_of_stock_count
        FROM sku
        WHERE is_active = 1
    """)
    stock_kpi = cursor.fetchone()

    cursor.execute("""
        SELECT
            p.name AS product_name,
            v.color,
            s.size,
            s.price,
            s.stock,
            s.sku_code
        FROM sku s
        JOIN variant v ON s.variant_id = v.id
        JOIN product p ON v.product_id = p.id
        WHERE s.is_active = 1
          AND s.stock <= 5
        ORDER BY s.stock ASC, p.id ASC
    """)
    low_stock_items = cursor.fetchall()

    # 4. 客戶貢獻度 (修正: 扣除退貨)
    cursor.execute("""
        SELECT
            COALESCE(c.name, o.name, '未知顧客') AS customer_name,
            COUNT(DISTINCT o.id) AS order_count,
            COALESCE(SUM(o.total), 0) - COALESCE(SUM(rr_total.refunded_amount), 0) AS total_spent
        FROM orders o
        LEFT JOIN customer c ON o.customer_id = c.id
        LEFT JOIN (
            SELECT rr.order_id, SUM(ri.qty * oi.unit_price) AS refunded_amount
            FROM return_request rr
            JOIN return_item ri ON rr.id = ri.return_request_id
            JOIN order_item oi ON ri.order_item_id = oi.id
            WHERE rr.status = 'refunded'
            GROUP BY rr.order_id
        ) rr_total ON o.id = rr_total.order_id
        WHERE DATE(o.created_at) BETWEEN %s AND %s
          AND o.status IN ('shipped', 'completed', 'refunded')
        GROUP BY COALESCE(c.name, o.name, '未知顧客')
        ORDER BY total_spent DESC
        LIMIT 10
    """, (start_date, end_date))
    top_customers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'staff/statistic_sales.html',
        start_date=start_date,
        end_date=end_date,
        product_sales=product_sales,
        category_sales=category_sales,
        stock_kpi=stock_kpi,
        low_stock_items=low_stock_items,
        top_customers=top_customers
    )