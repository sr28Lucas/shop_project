from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, flash
from app.db import get_db_connection
from datetime import datetime

wishlist_bp = Blueprint('wishlist', __name__)

def get_or_create_wishlist(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id FROM wishlist WHERE customer_id = %s", (customer_id,))
    wishlist = cursor.fetchone()
    
    if not wishlist:
        cursor.execute("INSERT INTO wishlist (customer_id, created_at, updated_at) VALUES (%s, %s, %s)",
                       (customer_id, datetime.now(), datetime.now()))
        conn.commit()
        wishlist_id = cursor.lastrowid
    else:
        wishlist_id = wishlist['id']
        
    cursor.close()
    conn.close()
    return wishlist_id

@wishlist_bp.route('/')
def index():
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('auth.login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取願望清單商品
    sql = """
        SELECT p.id, p.name, 
               MIN(s.price) as min_price,
               (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image
        FROM wishlist_item wi
        JOIN wishlist w ON wi.wishlist_id = w.id
        JOIN product p ON wi.product_id = p.id
        LEFT JOIN variant v ON p.id = v.product_id
        LEFT JOIN sku s ON v.id = s.variant_id
        WHERE w.customer_id = %s AND p.is_active = 1
        GROUP BY p.id
    """
    cursor.execute(sql, (customer_id,))
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('home/wishlist.html', items=items)

@wishlist_bp.route('/toggle/<int:product_id>', methods=['POST'])
def toggle(product_id):
    customer_id = session.get('customer_id')
    if not customer_id:
        return jsonify({'success': False, 'message': '請先登入', 'need_login': True}), 401
        
    wishlist_id = get_or_create_wishlist(customer_id)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 檢查是否已存在
    cursor.execute("SELECT 1 FROM wishlist_item WHERE wishlist_id = %s AND product_id = %s", 
                   (wishlist_id, product_id))
    exists = cursor.fetchone()
    
    if exists:
        # 移除
        cursor.execute("DELETE FROM wishlist_item WHERE wishlist_id = %s AND product_id = %s",
                       (wishlist_id, product_id))
        action = 'removed'
        message = '已從願望清單移除'
    else:
        # 新增
        cursor.execute("INSERT INTO wishlist_item (wishlist_id, product_id, created_at, updated_at) VALUES (%s, %s, %s, %s)",
                       (wishlist_id, product_id, datetime.now(), datetime.now()))
        action = 'added'
        message = '已加入願望清單'
        
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True, 'action': action, 'message': message})

@wishlist_bp.route('/remove/<int:product_id>', methods=['POST'])
def remove(product_id):
    customer_id = session.get('customer_id')
    if not customer_id:
        return redirect(url_for('auth.login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        DELETE wi FROM wishlist_item wi
        JOIN wishlist w ON wi.wishlist_id = w.id
        WHERE w.customer_id = %s AND wi.product_id = %s
    """, (customer_id, product_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('商品已從願望清單移除')
    return redirect(url_for('home.wishlist.index'))
