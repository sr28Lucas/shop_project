from flask import Blueprint, render_template, request, get_flashed_messages, session, redirect, url_for, flash, jsonify
from app.db import get_db_connection
from datetime import datetime
from app.services.gemini_service import GeminiService

home_bp = Blueprint('home', __name__, template_folder='../../templates/home')
gemini_service = GeminiService()

@home_bp.route('/api/chat', methods=['POST'])
def chat():
    user_query = request.json.get('query')
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get all active products for context
    cursor.execute("SELECT id, name, description FROM product WHERE is_active = 1 AND is_deleted = 0")
    products = cursor.fetchall()
    cursor.close()
    conn.close()

    product_context = "\n".join([f"- {p['name']} (ID: {p['id']}): {p['description']}" for p in products])
    
    try:
        recommendation = gemini_service.get_recommendation(user_query, product_context)
        return jsonify({'response': recommendation})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    
    # 獲取所有未被軟刪除的分類
    cursor.execute("SELECT id, name FROM category WHERE is_deleted = 0 ORDER BY id ASC")
    categories = cursor.fetchall()
    
    # 獲取商品、最低/最高價格及首圖 (忽略被軟刪除的商品)
    sql = """
        SELECT 
            p.id, p.name, 
            MIN(s.price) as min_price, 
            MAX(s.price) as max_price,
            (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image
        FROM product p
        LEFT JOIN variant v ON p.id = v.product_id
        LEFT JOIN sku s ON v.id = s.variant_id
        WHERE p.is_active = 1 AND p.is_deleted = 0
          AND (s.is_active = 1 OR s.is_active IS NULL) AND (s.is_deleted = 0 OR s.is_deleted IS NULL)
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
    
    # 獲取有效公告：active=1 且 在開始與結束時間內 (或未設定時間)，且未被軟刪除
    cursor.execute("""
        SELECT * FROM announcement 
        WHERE is_active = 1 AND is_deleted = 0
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
    
    # 獲取商品基本資料與分類名稱，並嘗試獲取第一張主圖作為預設 (檢查 is_deleted)
    cursor.execute("""
        SELECT p.*, c.name as category_name,
        (SELECT filename FROM image WHERE product_id = p.id AND image_type = 'product' ORDER BY sort_order ASC LIMIT 1) as main_image
        FROM product p 
        LEFT JOIN category c ON p.category_id = c.id 
        WHERE p.id = %s AND p.is_active = 1 AND p.is_deleted = 0
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

    # 獲取所有未刪除且啟用的 SKU
    cursor.execute("""
        SELECT s.*, v.color FROM sku s
        JOIN variant v ON s.variant_id = v.id
        WHERE v.product_id = %s AND s.is_active = 1 AND s.is_deleted = 0
    """, (id,))
    skus = cursor.fetchall()

    # 獲取所有未刪除且啟用的變體 (Colors)
    cursor.execute("SELECT * FROM variant WHERE product_id = %s AND is_active = 1 AND is_deleted = 0", (id,))
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

    # === 🌟 旗艦版評價系統：一次算出所有聚合數據 ===
    stats_query = """
        SELECT 
            COUNT(id) as total_reviews,
            COALESCE(AVG(overall_rating), 0) as avg_overall,
            COALESCE(AVG(quality_rating), 0) as avg_quality,
            COALESCE(AVG(comfort_rating), 0) as avg_comfort,
            COALESCE(AVG(value_rating), 0) as avg_value,
            SUM(CASE WHEN fit_feedback = -1 THEN 1 ELSE 0 END) as fit_small_count,
            SUM(CASE WHEN fit_feedback = 0 THEN 1 ELSE 0 END) as fit_normal_count,
            SUM(CASE WHEN fit_feedback = 1 THEN 1 ELSE 0 END) as fit_large_count
        FROM review 
        WHERE product_id = %s
    """
    cursor.execute(stats_query, (id,))
    stats = cursor.fetchone()
    
    total_reviews = stats['total_reviews']
    if total_reviews > 0:
        stats['fit_small_pct'] = round((stats['fit_small_count'] / total_reviews) * 100)
        stats['fit_normal_pct'] = round((stats['fit_normal_count'] / total_reviews) * 100)
        stats['fit_large_pct'] = round((stats['fit_large_count'] / total_reviews) * 100)
    else:
        stats['fit_small_pct'] = stats['fit_normal_pct'] = stats['fit_large_pct'] = 0

    # === 🌟 撈取個別的文字留言與買家匿名化 ===
    cursor.execute("""
        SELECT 
            r.*, 
            CONCAT(SUBSTRING(c.name, 1, 1), '***', SUBSTRING(c.name, LENGTH(c.name), 1)) as anonymous_name,
            oi.color, 
            oi.size
        FROM review r
        JOIN customer c ON r.customer_id = c.id
        JOIN order_item oi ON r.order_item_id = oi.id
        WHERE r.product_id = %s
        ORDER BY r.created_at DESC
    """, (id,))
    reviews = cursor.fetchall()

    cursor.close()
    conn.close()
    
    # 記得將 stats 與 reviews 傳遞給前端！
    return render_template('home/product_view.html', product=product, product_images=product_images, variants=variants, is_in_wishlist=is_in_wishlist, stats=stats, reviews=reviews)


# ==============================================================
# 🌟 新增：接收客人提交評價的 API
# ==============================================================
@home_bp.route('/add_review', methods=['POST'])
def add_review():
    if 'customer_id' not in session:
        flash("請先登入後再填寫評價")
        return redirect(url_for('auth.login'))
        
    customer_id = session['customer_id']
    product_id = request.form.get('product_id')
    order_item_id = request.form.get('order_item_id')
    
    overall_rating = request.form.get('overall_rating')
    quality_rating = request.form.get('quality_rating')
    comfort_rating = request.form.get('comfort_rating')
    value_rating = request.form.get('value_rating')
    fit_feedback = request.form.get('fit_feedback') # -1, 0, 1
    comment = request.form.get('comment')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 驗證 1：確認這個 order_item 真的屬於這個客人，且買的是這個商品
        cursor.execute("""
            SELECT oi.id FROM order_item oi
            JOIN orders o ON oi.order_id = o.id
            WHERE oi.id = %s AND o.customer_id = %s AND oi.product_id = %s
        """, (order_item_id, customer_id, product_id))
        
        if not cursor.fetchone():
            flash("找不到購買紀錄，無法評價")
            return redirect(request.referrer)
            
        # 驗證 2：確認沒有重複評價 (用 order_item_id 當唯一憑證)
        cursor.execute("SELECT id FROM review WHERE order_item_id = %s", (order_item_id,))
        if cursor.fetchone():
            flash("這筆訂單的商品您已經評價過囉！")
            return redirect(request.referrer)

        # 寫入評價
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO review (customer_id, product_id, order_item_id, overall_rating, quality_rating, comfort_rating, value_rating, fit_feedback, comment, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, product_id, order_item_id, overall_rating, quality_rating, comfort_rating, value_rating, fit_feedback, comment, now))
        
        conn.commit()
        flash("感謝您的評價！")
        
    except Exception as e:
        conn.rollback()
        print(f"評價錯誤: {e}")
        flash("評價失敗，請稍後再試。")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(request.referrer)