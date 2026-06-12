from flask import Blueprint, render_template, request, get_flashed_messages, session
from app.db import get_db_connection

home_bp = Blueprint('home', __name__, template_folder='../../templates/home')

@home_bp.route('/api/regions')
def get_regions():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM region")
    regions = cursor.fetchall()
    cursor.close()
    conn.close()
    return {'regions': regions}

@home_bp.route('/api/localities/<int:region_id>')
def get_localities(region_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name FROM locality WHERE region_id = %s", (region_id,))
    localities = cursor.fetchall()
    cursor.close()
    conn.close()
    return {'localities': [l['name'] for l in localities]}

from .checkout import checkout_bp
home_bp.register_blueprint(checkout_bp, url_prefix='/checkout')

from .support import support_bp
home_bp.register_blueprint(support_bp, url_prefix='/support')

from .wishlist import wishlist_bp
home_bp.register_blueprint(wishlist_bp, url_prefix='/wishlist')


@home_bp.route('/')
def index():
    query = request.args.get('q', '')
    cat_id = request.args.get('cat', type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取所有分類
    cursor.execute("SELECT id, name FROM category ORDER BY id ASC")
    categories = cursor.fetchall()
    
    # 獲取商品、最低/最高價格及首圖
    sql = """
        SELECT 
            p.id, p.name, 
            MIN(s.price) as min_price, 
            MAX(s.price) as max_price,
            (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image
        FROM product p
        LEFT JOIN variant v ON p.id = v.product_id
        LEFT JOIN sku s ON v.id = s.variant_id
        WHERE p.is_active = 1
          AND (s.is_active = 1 OR s.is_active IS NULL) 
    """
    params = []
    if query:
        sql += " AND p.name LIKE %s"
        params.append(f"%{query}%")
    
    if cat_id:
        sql += " AND p.category_id = %s"
        params.append(cat_id)
    
    sql += " GROUP BY p.id"
    
    cursor.execute(sql, params)
    products = cursor.fetchall()
    
    # 獲取當前分類名稱 (如果是全商品則為None)
    current_category_name = None
    if cat_id:
        for c in categories:
            if c['id'] == cat_id:
                current_category_name = c['name']
                break
    
    cursor.close()
    conn.close()
    return render_template('home/index.html', products=products, categories=categories, current_cat_id=cat_id, current_category_name=current_category_name)

@home_bp.route('/hot_items')
def hot_items():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取熱銷商品 (前10名，依據過去7天銷售量，同名次按ID序)
    cursor.execute("""
        SELECT 
            p.id, p.name, 
            MIN(s.price) as min_price, 
            MAX(s.price) as max_price,
            (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image,
            SUM(oi.qty) as total_sold
        FROM product p
        JOIN order_item oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        LEFT JOIN variant v ON p.id = v.product_id
        LEFT JOIN sku s ON v.id = s.variant_id
        WHERE p.is_active = 1
          AND o.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY p.id
        ORDER BY total_sold DESC, p.id ASC
        LIMIT 10
    """)
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('home/hot_items.html', items=items)

@home_bp.route('/announcements')
def announcements():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取有效公告：active=1 且 在開始與結束時間內 (或未設定時間)
    cursor.execute("""
        SELECT * FROM announcement 
        WHERE is_active = 1 
          AND (start_at IS NULL OR start_at <= NOW())
          AND (end_at IS NULL OR end_at >= NOW())
        ORDER BY pin DESC, created_at DESC
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

def sort_sizes(skus):
    """
    自定義尺寸排序規則：
    1. 標準尺寸順序：XS, S, M, L, XL, 2XL, 3XL, 4XL, 5XL
    2. 數字尺寸 (例如 36, 38)
    3. 其他字母或文字
    """
    size_order = {
        'XXS': 1, 'XS': 2, 'S': 3, 'M': 4, 'L': 5, 'XL': 6, 
        '2XL': 7, 'XXL': 7, '3XL': 8, 'XXXL': 8, '4XL': 9, '5XL': 10,
        'F': 20, 'FREE': 20
    }
    
    def get_sort_key(sku):
        size = str(sku['size']).upper().strip()
        if size in size_order:
            return (0, size_order[size], size)
        
        # 嘗試轉換為數字
        try:
            # 處理像 "36" 或 "36.5"
            return (1, float(size), size)
        except ValueError:
            return (2, 0, size)
            
    return sorted(skus, key=get_sort_key)

@home_bp.route('/product/<int:id>')
def product_view(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取商品基本資料與分類名稱，並嘗試獲取第一張主圖作為預設
    cursor.execute("""
        SELECT p.*, c.name as category_name,
        (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image
        FROM product p 
        LEFT JOIN category c ON p.category_id = c.id 
        WHERE p.id = %s AND p.is_active = 1
    """, (id,))
    product = cursor.fetchone()
    
    if not product:
        cursor.close()
        conn.close()
        return "商品不存在", 404
        
    # 獲取商品所有相關圖片
    cursor.execute("SELECT * FROM image WHERE product_id = %s ORDER BY sort_order", (id,))
    all_images = cursor.fetchall()
    
    product_images = [img for img in all_images if img['image_type'] == 'product']
    # 建立 variant_id 到 filename 的對應 (假設每個 variant 只有一張圖，或取第一張)
    variant_images = {img['variant_id']: img['filename'] for img in all_images if img['variant_id']}

    # 獲取所有 SKU
    cursor.execute("""
        SELECT s.*, v.color FROM sku s
        JOIN variant v ON s.variant_id = v.id
        WHERE v.product_id = %s AND s.is_active = 1
    """, (id,))
    skus = cursor.fetchall()

    # 獲取所有變體 (Colors)
    cursor.execute("SELECT * FROM variant WHERE product_id = %s AND is_active = 1", (id,))
    variants = cursor.fetchall()
    for v in variants:
        # 將 SKU 關聯到對應的變體，並進行尺寸排序
        v_skus = [s for s in skus if s['variant_id'] == v['id']]
        v['skus'] = sort_sizes(v_skus)
        # 關聯圖片
        v['image'] = variant_images.get(v['id'])

    # 檢查是否已在願望清單
    is_in_wishlist = False
    customer_id = session.get('customer_id')
    if customer_id:
        cursor.execute("""
            SELECT 1 FROM wishlist_item wi
            JOIN wishlist w ON wi.wishlist_id = w.id
            WHERE w.customer_id = %s AND wi.product_id = %s
        """, (customer_id, id))
        if cursor.fetchone():
            is_in_wishlist = True

    cursor.close()
    conn.close()
    return render_template('home/product_view.html', product=product, product_images=product_images, variants=variants, is_in_wishlist=is_in_wishlist)
