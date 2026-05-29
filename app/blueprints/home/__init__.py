from flask import Blueprint, render_template, request, get_flashed_messages, session
from app.db import get_db_connection

home_bp = Blueprint('home', __name__, template_folder='../../templates/home')

@home_bp.route('/')
def index():
    query = request.args.get('q', '')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取商品、最低/最高價格及首圖
    sql = """
        SELECT 
            p.id, p.name, 
            MIN(s.price) as min_price, 
            MAX(s.price) as max_price,
            (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image
        FROM product p
        LEFT JOIN sku s ON p.id = s.product_id
        WHERE p.is_active = 1 AND p.is_deleted = 0 
          AND (s.is_active = 1 OR s.is_active IS NULL) 
          AND (s.is_deleted = 0 OR s.is_deleted IS NULL)
    """
    params = []
    if query:
        sql += " AND p.name LIKE %s"
        params.append(f"%{query}%")
    
    sql += " GROUP BY p.id"
    
    cursor.execute(sql, params)
    products = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('home/index.html', products=products)

@home_bp.route('/announcements')
def announcements():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT * FROM announcement 
        WHERE is_active = 1 
        ORDER BY priority DESC, created_at DESC
    """)
    announcements = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('home/announcements.html', announcements=announcements)

@home_bp.route('/announcement/<int:id>')
def announcement_view(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM announcement WHERE id = %s AND is_active = 1", (id,))
    announcement = cursor.fetchone()
    cursor.close()
    conn.close()
    if not announcement:
        return "公告不存在", 404
    return render_template('home/announcement_view.html', announcement=announcement)

@home_bp.route('/product/<int:id>')
def product_view(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取商品基本資料與分類名稱
    cursor.execute("""
        SELECT p.*, c.name as category_name 
        FROM product p 
        JOIN category c ON p.category_id = c.id 
        WHERE p.id = %s AND p.is_active = 1 AND p.is_deleted = 0 AND c.is_deleted = 0
    """, (id,))
    product = cursor.fetchone()
    
    if not product:
        cursor.close()
        conn.close()
        return "商品不存在", 404
        
    # 獲取商品圖片
    cursor.execute("SELECT * FROM image WHERE product_id = %s AND image_type = 'product' ORDER BY sort_order", (id,))
    images = cursor.fetchall()
    
    # 獲取所有 SKU
    cursor.execute("""
        SELECT * FROM sku 
        WHERE product_id = %s AND is_active = 1 AND is_deleted = 0
        ORDER BY price ASC
    """, (id,))
    skus = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('home/product_view.html', product=product, images=images, skus=skus)
