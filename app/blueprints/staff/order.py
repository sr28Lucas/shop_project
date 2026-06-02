from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import get_db_connection
from datetime import datetime
import json
import os
from app.config import config

order_bp = Blueprint('order', __name__)

@order_bp.route('/logistics_settings', methods=['GET', 'POST'])
def logistics_settings():
    json_path = os.path.join(config.BASE_DIR, 'app', 'static', 'json', 'taiwan_districts.json')
    
    if request.method == 'POST':
        new_data = {}
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for city in data:
            fee = request.form.get(f'fee_{city}')
            if fee:
                data[city]['fee'] = float(fee)
                
                # 同步更新資料庫
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE region SET fee = %s WHERE name = %s", (float(fee), city))
                conn.commit()
                cursor.close()
                conn.close()

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        flash('運費設定已更新')
        return redirect(url_for('staff.order.logistics_settings'))

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    return render_template('staff/logistics_settings.html', data=data)

@order_bp.route('/list')
def order_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 查詢訂單列表，只顯示處理中或輸送中，包含客戶資訊與出貨狀態
    query = """
    SELECT o.*, c.name as customer_name, s.status as shipment_status
    FROM orders o
    LEFT JOIN customer c ON o.customer_id = c.id
    LEFT JOIN shipment s ON o.id = s.order_id
    WHERE (s.status IN ('pending', 'shipped') OR s.status IS NULL) 
      AND o.status != 'cancelled'
    ORDER BY o.created_at DESC
    """
    cursor.execute(query)
    orders = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('staff/order_list.html', orders=orders)

@order_bp.route('/history')
def order_history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 查詢訂單列表，顯示已完成或已取消，或訂單狀態為已取消
    query = """
    SELECT DISTINCT o.*, c.name as customer_name, s.status as shipment_status
    FROM orders o
    LEFT JOIN customer c ON o.customer_id = c.id
    LEFT JOIN order_item oi ON o.id = oi.order_id
    LEFT JOIN shipment s ON o.id = s.order_id
    WHERE s.status IN ('delivered') OR o.status = 'cancelled'
    ORDER BY o.created_at DESC
    """
    cursor.execute(query)
    orders = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('staff/order_history.html', orders=orders)

@order_bp.route('/cancel/<int:id>', methods=['POST'])
def cancel_order(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 將訂單狀態設為 'cancelled'
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", ('cancelled', id))
        conn.commit()
        flash(f"訂單 {id} 已取消")
    except Exception as e:
        conn.rollback()
        flash(f"取消失敗: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.order.order_list'))

@order_bp.route('/bulk_update_shipment', methods=['POST'])
def bulk_update_shipment():
    order_ids = request.form.getlist('order_ids')
    status = request.form.get('status')
    
    if not order_ids or not status:
        flash("請先勾選訂單並選擇狀態")
        return redirect(url_for('staff.order.order_list'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for order_id in order_ids:
            # 更新或插入 shipment 狀態
            cursor.execute("""
                INSERT INTO shipment (order_id, status, shipped_at, delivered_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                status = VALUES(status),
                shipped_at = CASE WHEN VALUES(status) = 'shipped' THEN NOW() ELSE shipped_at END,
                delivered_at = CASE WHEN VALUES(status) = 'delivered' THEN NOW() ELSE delivered_at END
            """, (order_id, status, 
                  datetime.now() if status == 'shipped' else None,
                  datetime.now() if status == 'delivered' else None))
        conn.commit()
        flash("出貨狀態已更新")
    except Exception as e:
        conn.rollback()
        flash(f"更新失敗: {e}")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('staff.order.order_list'))

@order_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def order_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        item_id = request.form.get('item_id')
        if item_id:
            cursor.execute("DELETE FROM order_item WHERE id = %s AND order_id = %s", (item_id, id))
            conn.commit()
            flash("已移除訂單項目")
        return redirect(url_for('staff.order.order_edit', id=id))

    cursor.execute("SELECT o.*, c.name as customer_name FROM orders o LEFT JOIN customer c ON o.customer_id = c.id WHERE o.id = %s", (id,))
    order = cursor.fetchone()
    
    cursor.execute("SELECT * FROM order_item WHERE order_id = %s", (id,))
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('staff/order_edit.html', order=order, items=items)
