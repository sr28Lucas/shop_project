from flask import Blueprint, session, request, redirect, render_template, url_for, flash 
from werkzeug.utils import secure_filename
from app.db import get_db_connection
from datetime import datetime
from app.config import config
import os
from .permission import require_permission
from app.utils.validators import Validator
from app.models.product_model import ProductModel
from app.models.category_model import CategoryModel

product_bp = Blueprint('product', __name__)

@product_bp.route('/list')
@require_permission('product')
def product_list():
    category_id = request.args.get('category_id')
    is_active = request.args.get('is_active')
    
    # 使用 ProductModel 或調整查詢以包含 is_deleted=0
    query = """
    SELECT p.*, c.name as category_name
    FROM product p 
    LEFT JOIN category c ON p.category_id = c.id
    WHERE p.is_deleted = 0 
    """

    params = []
    
    if category_id:
        query += " AND p.category_id = %s"
        params.append(category_id)
    if is_active:
        query += " AND p.is_active = %s"
        params.append(is_active)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, params)
    products = cursor.fetchall()
    
    categories = CategoryModel.get_all()
    conn.close()

    return render_template('staff/product_list.html', products=products, categories=categories)


@product_bp.route('/add', methods=['GET', 'POST'])
@require_permission('product')
def product_add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id')
        description = request.form.get('description', '').strip()
        files = request.files.getlist('images')

        if not category_id:
            return "商品必須選擇分類", 400
        
        if not Validator.is_valid_length(name, 100, 1):
            return "商品名稱長度需在 1-100 字元之間", 400
        
        if not Validator.is_valid_length(description, 2000):
            return "商品描述長度不能超過 2000 字元", 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM product WHERE name = %s AND is_deleted = 0", (name,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return "商品名稱已存在", 400

        if not os.path.exists(config.UPLOAD_FOLDER):
            os.makedirs(config.UPLOAD_FOLDER)

        try:
            cursor.execute("""
                INSERT INTO product (category_id, name, description, is_active, is_deleted, created_at, updated_at)
                VALUES (%s, %s, %s, 1, 0, NOW(), NOW())
            """, (category_id, name, description))
            
            product_id = cursor.lastrowid
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for index, file in enumerate(files):
                if file:
                    cursor.execute("""
                        INSERT INTO image (product_id, filename, sort_order, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (product_id, "", index, now, now)) 
                    
                    image_id = cursor.lastrowid
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"{product_id}_{image_id}{ext}"
                    upload_path = os.path.join(config.UPLOAD_FOLDER, filename)
                    file.save(upload_path)
                    
                    cursor.execute("UPDATE image SET filename = %s WHERE id = %s", (filename, image_id))

            conn.commit()
            return "OK", 200

        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return "Internal Server Error", 500
        finally:
            cursor.close()
            conn.close()

    categories = CategoryModel.get_all()
    return render_template('staff/product_add.html', categories = categories)


@product_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@require_permission('product')
def product_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id')
        description = request.form.get('description', '').strip()
        
        if not category_id:
            cursor.close()
            conn.close()
            return "商品必須選擇分類", 400
        
        if not Validator.is_valid_length(name, 100, 1):
            cursor.close()
            conn.close()
            return "商品名稱長度需在 1-100 字元之間", 400
        
        if not Validator.is_valid_length(description, 2000):
            cursor.close()
            conn.close()
            return "商品描述長度不能超過 2000 字元", 400

        image_order = request.form.get('image_order').split(',')
        deleted_ids = request.form.get('deleted_ids')
        new_files = request.files.getlist('images')

        cursor.execute("SELECT id FROM product WHERE name = %s AND id != %s AND is_deleted = 0", (name, id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return "商品名稱已存在", 400

        try:
            cursor.execute("""
                UPDATE product 
                SET category_id=%s, name=%s, description=%s, updated_at=NOW()
                WHERE id=%s
            """, (category_id, name, description, id))

            if deleted_ids:
                id_list = [int(i) for i in deleted_ids.split(',') if i]
                for d_id in id_list:
                    cursor.execute("SELECT filename FROM image WHERE id=%s", (d_id,))
                    img_data = cursor.fetchone()
                    if img_data:
                        file_path = os.path.join(config.UPLOAD_FOLDER, img_data['filename'])
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    cursor.execute("DELETE FROM image WHERE id=%s", (d_id,))

            new_file_index = 0
            for index, item_tag in enumerate(image_order):
                if not item_tag: continue
                
                if item_tag.startswith('old_'):
                    old_id = item_tag.split('_')[1]
                    cursor.execute("UPDATE image SET sort_order=%s WHERE id=%s", (index, old_id))
                
                elif item_tag.startswith('new_'):
                    file = new_files[new_file_index]
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    cursor.execute("""
                        INSERT INTO image (product_id, filename, sort_order, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (id, "", index, now, now))
                    
                    new_img_id = cursor.lastrowid
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"{id}_{new_img_id}{ext}"
                    file.save(os.path.join(config.UPLOAD_FOLDER, filename))
                    cursor.execute("UPDATE image SET filename = %s WHERE id = %s", (filename, new_img_id))
                    
                    new_file_index += 1

            conn.commit()
            return "OK", 200

        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return str(e), 500
        finally:
            cursor.close()
            conn.close()

    cursor.execute("SELECT * FROM product WHERE id = %s AND is_deleted = 0", (id,))
    product = cursor.fetchone()
    
    cursor.execute("SELECT * FROM image WHERE product_id = %s ORDER BY sort_order", (id,))
    images = cursor.fetchall()
    
    categories = CategoryModel.get_all()
    
    conn.close()
    return render_template('staff/product_edit.html', product=product, images=images, categories=categories)


@product_bp.route('/bulk_update_status', methods=['POST'])
@require_permission('product')
def bulk_update_status():
    product_ids = request.form.getlist('product_ids')
    action = request.form.get('action')
    
    if not product_ids:
        flash("請先勾選商品")
        return redirect(url_for('staff.product.product_list'))
        
    if action == 'on':
        is_active = 1
    elif action == 'off':
        is_active = 0
    else:
        flash("無效的操作")
        return redirect(url_for('staff.product.product_list'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ','.join(['%s'] * len(product_ids))
        cursor.execute(f"UPDATE product SET is_active = %s, updated_at = NOW() WHERE id IN ({format_strings}) AND is_deleted = 0", [is_active] + product_ids)
        conn.commit()
        flash(f"已成功更新 {cursor.rowcount} 個商品狀態")
    except Exception as e:
        conn.rollback()
        flash(f"批次更新失敗: {e}")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('staff.product.product_list'))


@product_bp.route('/delete/<int:id>', methods=['POST'])
@require_permission('product')
def product_delete(id):
    # 使用 ProductModel 的軟刪除方法
    try:
        ProductModel.soft_delete(id)
        # 可選：對關聯的 variant/sku 也進行軟刪除 (此處維持原邏輯，但改為軟刪除)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE sku SET is_deleted = 1 WHERE variant_id IN (SELECT id FROM variant WHERE product_id = %s)", (id,))
        cursor.execute("UPDATE variant SET is_deleted = 1 WHERE product_id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash("商品已刪除")
    except Exception as e:
        flash(f"刪除失敗: {str(e)}")
    return redirect(url_for('staff.product.product_list'))


@product_bp.route('/<int:product_id>/variant')
@require_permission('product')
def variant_list(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name FROM product WHERE id = %s AND is_deleted = 0", (product_id,))
    product = cursor.fetchone()
    
    # 過濾已被軟刪除的變體與SKU
    cursor.execute("SELECT * FROM variant WHERE product_id = %s AND is_deleted = 0", (product_id,))
    variants = cursor.fetchall()
    cursor.execute("""
        SELECT s.*, v.color 
        FROM sku s
        JOIN variant v ON s.variant_id = v.id
        WHERE v.product_id = %s AND s.is_deleted = 0
    """, (product_id,))
    skus = cursor.fetchall()
    
    for v in variants:
        v['skus'] = [s for s in skus if s['variant_id'] == v['id']]
    cursor.close()
    conn.close()
    return render_template("staff/variant_list.html", product_id=product_id, product_name=product['name'] if product else "未知商品", variants=variants)


@product_bp.route('/<int:product_id>/variant/add', methods=['GET', 'POST'])
@require_permission('product')
def variant_add(product_id):
    if request.method == 'POST':
        color = request.form.get('color')
        is_active = 1 if request.form.get('variant_is_active') else 0 # 0 代表隱藏下架
        variant_image_file = request.files.get('variant_image')
        
        sku_codes = request.form.getlist("sku_code[]")
        sizes = request.form.getlist("size[]")
        prices = request.form.getlist("price[]")
        costs = request.form.getlist("cost[]")
        stocks = request.form.getlist("stock[]")
        active_indices = request.form.getlist("is_active[]")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # === 新增：內部分類檢查與值域檢查 ===
            seen_sku_codes = set()
            for i in range(len(sku_codes)):
                sku_code = sku_codes[i]
                price = float(prices[i])
                cost = float(costs[i])
                stock = int(stocks[i])

                if sku_code in seen_sku_codes:
                    flash(f"新增失敗：表單中包含重複的貨號 '{sku_code}'！")
                    return redirect(url_for('staff.product.variant_list', product_id=product_id))
                seen_sku_codes.add(sku_code)

                if not Validator.is_valid_number(price, 999999999) or \
                   not Validator.is_valid_number(cost, 999999999) or \
                   not Validator.is_valid_number(stock, 1000000):
                    flash(f"新增失敗：價格/成本上限 9.9億，庫存上限 100萬，且不能為負數！")
                    return redirect(url_for('staff.product.variant_list', product_id=product_id))

            # === 防呆檢查 sku_code 是否重複於資料庫 (排除已刪除) ===
            for sku_code in sku_codes:
                cursor.execute("SELECT id FROM sku WHERE sku_code = %s AND is_deleted = 0", (sku_code,))
                if cursor.fetchone():
                    flash(f"新增失敗：貨號 '{sku_code}' 已經存在且正在使用中！")
                    return redirect(url_for('staff.product.variant_list', product_id=product_id))
            # ========================================

            cursor.execute("INSERT INTO variant (product_id, color, is_active, is_deleted, created_at, updated_at) VALUES (%s, %s, %s, 0, NOW(), NOW())", (product_id, color, is_active))
            variant_id = cursor.lastrowid
            
            if variant_image_file:
                cursor.execute("""
                    INSERT INTO image (product_id, variant_id, image_type, filename, sort_order, created_at, updated_at)
                    VALUES (%s, %s, 'variant', '', 0, NOW(), NOW())
                """, (product_id, variant_id))
                new_img_id = cursor.lastrowid
                ext = os.path.splitext(variant_image_file.filename)[1]
                filename = f"v_{variant_id}_{new_img_id}{ext}"
                if not os.path.exists(config.UPLOAD_FOLDER):
                    os.makedirs(config.UPLOAD_FOLDER)
                variant_image_file.save(os.path.join(config.UPLOAD_FOLDER, filename))
                cursor.execute("UPDATE image SET filename = %s WHERE id = %s", (filename, new_img_id))
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for i in range(len(sizes)):
                sku_code = sku_codes[i]
                size = sizes[i]
                price = float(prices[i])
                cost = float(costs[i])
                stock = int(stocks[i])
                is_sku_active = 1 if str(i) in active_indices else 0
                
                cursor.execute("""
                    INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, is_deleted, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s)
                """, (variant_id, sku_code, size, price, cost, stock, is_sku_active, now, now))
                
            conn.commit()
            flash("新增變體與規格成功")
            return redirect(url_for('staff.product.variant_list', product_id=product_id))
        except Exception as e:
            conn.rollback()
            flash(f"新增失敗: {str(e)}")
        finally:
            cursor.close()
            conn.close()
    return render_template('staff/variant_add.html', product_id=product_id)


@product_bp.route('/<int:product_id>/variant/<int:variant_id>/edit', methods=['GET', 'POST'])
@require_permission('product')
def variant_edit(product_id, variant_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM variant WHERE id = %s AND product_id = %s", (variant_id, product_id))
    variant = cursor.fetchone()
    
    if not variant:
        cursor.close()
        conn.close()
        flash("找不到該變體")
        return redirect(url_for('staff.product.variant_list', product_id=product_id))

    if request.method == "POST":
        color = request.form.get("color")
        variant_is_active = 1 if request.form.get("variant_is_active") else 0
        sku_ids = request.form.getlist("sku_id[]")
        sku_codes = request.form.getlist("sku_code[]")
        sizes = request.form.getlist("size[]")
        prices = request.form.getlist("price[]")
        costs = request.form.getlist("cost[]")
        stocks = request.form.getlist("stock[]")
        active_indices = request.form.getlist("is_active[]")
        print(f"DEBUG: active_indices from form: {active_indices}")
        
        variant_image_file = request.files.get('variant_image')
        delete_image = request.form.get('delete_image') == '1'
        
        try:
            # === 新增：內部分類檢查與值域檢查 ===
            seen_sku_codes = set()
            for i in range(len(sizes)):
                sku_code = sku_codes[i]
                price = float(prices[i])
                cost = float(costs[i])
                stock = int(stocks[i])

                if sku_code in seen_sku_codes:
                    flash(f"修改失敗：表單中包含重複的貨號 '{sku_code}'！")
                    return redirect(url_for('staff.product.variant_edit', product_id=product_id, variant_id=variant_id))
                seen_sku_codes.add(sku_code)

                if not Validator.is_valid_number(price, 999999999) or \
                   not Validator.is_valid_number(cost, 999999999) or \
                   not Validator.is_valid_number(stock, 1000000):
                    flash(f"修改失敗：價格/成本上限 9.9億，庫存上限 100萬，且不能為負數！")
                    return redirect(url_for('staff.product.variant_edit', product_id=product_id, variant_id=variant_id))

            # === 原有：防呆檢查 sku_code 是否重複於資料庫 ===
            for i in range(len(sizes)):
                s_id = int(sku_ids[i]) if (i < len(sku_ids) and sku_ids[i]) else None
                sku_code = sku_codes[i]
                
                # 如果是修改舊的 SKU，排除自己；如果是新的 SKU，直接查
                if s_id:
                    cursor.execute("SELECT id FROM sku WHERE sku_code = %s AND is_deleted = 0 AND id != %s", (sku_code, s_id))
                else:
                    cursor.execute("SELECT id FROM sku WHERE sku_code = %s AND is_deleted = 0", (sku_code,))
                    
                if cursor.fetchone():
                    flash(f"修改失敗：貨號 '{sku_code}' 已經存在且正在使用中！")
                    return redirect(url_for('staff.product.variant_edit', product_id=product_id, variant_id=variant_id))
            # ========================================

            cursor.execute("UPDATE variant SET color = %s, is_active = %s, updated_at = NOW() WHERE id = %s", (color, variant_is_active, variant_id))
            
            submitted_sku_ids = []
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for i in range(len(sizes)):
                s_id = int(sku_ids[i]) if (i < len(sku_ids) and sku_ids[i]) else None
                sku_code = sku_codes[i]
                size = sizes[i]
                price = float(prices[i])
                cost = float(costs[i])
                stock = int(stocks[i])
                # 標準化：選取了即為啟用(1)，否則為停用(0)
                is_active = 1 if str(i) in active_indices else 0
                
                if s_id: 
                    cursor.execute("""
                        UPDATE sku SET sku_code=%s, size=%s, price=%s, cost=%s, stock=%s, is_active=%s, updated_at=%s
                        WHERE id=%s AND variant_id=%s
                    """, (sku_code, size, price, cost, stock, is_active, now, s_id, variant_id))
                    submitted_sku_ids.append(s_id)
                else: 
                    cursor.execute("""
                        INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, is_deleted, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s)
                    """, (variant_id, sku_code, size, price, cost, stock, is_active, now, now))
                    submitted_sku_ids.append(cursor.lastrowid)
            
            # 移除 SKU 改為軟刪除 (標記為停用)
            if submitted_sku_ids:
                format_strings = ','.join(['%s'] * len(submitted_sku_ids))
                cursor.execute(f"UPDATE sku SET is_deleted = 1, is_active = 0 WHERE variant_id = %s AND id NOT IN ({format_strings})", [variant_id] + submitted_sku_ids)
            else:
                cursor.execute("UPDATE sku SET is_deleted = 1, is_active = 0 WHERE variant_id = %s", (variant_id,))

            if delete_image or variant_image_file:
                cursor.execute("SELECT id, filename FROM image WHERE variant_id = %s", (variant_id,))
                old_imgs = cursor.fetchall()
                for img in old_imgs:
                    file_path = os.path.join(config.UPLOAD_FOLDER, img['filename'])
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    cursor.execute("DELETE FROM image WHERE id = %s", (img['id'],))

            if variant_image_file:
                cursor.execute("""
                    INSERT INTO image (product_id, variant_id, image_type, filename, sort_order, created_at, updated_at)
                    VALUES (%s, %s, 'variant', '', 0, NOW(), NOW())
                """, (product_id, variant_id))
                new_img_id = cursor.lastrowid
                ext = os.path.splitext(variant_image_file.filename)[1]
                filename = f"v_{variant_id}_{new_img_id}{ext}"
                variant_image_file.save(os.path.join(config.UPLOAD_FOLDER, filename))
                cursor.execute("UPDATE image SET filename = %s WHERE id = %s", (filename, new_img_id))

            conn.commit()
            flash("變體修改成功")
            return redirect(url_for('staff.product.variant_list', product_id=product_id))
        except Exception as e:
            conn.rollback()
            flash(f"修改失敗: {str(e)}")
            return redirect(url_for('staff.product.variant_edit', product_id=product_id, variant_id=variant_id))
        finally:
            cursor.close()
            conn.close()
        
    cursor.execute("SELECT * FROM sku WHERE variant_id = %s AND is_deleted = 0", (variant_id,))
    skus = cursor.fetchall()
    cursor.execute("SELECT * FROM image WHERE variant_id = %s LIMIT 1", (variant_id,))
    image = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("staff/variant_edit.html", variant=variant, skus=skus, product_id=product_id, image=image)

@product_bp.route('/<int:product_id>/variant/<int:variant_id>/delete', methods=['POST'])
@require_permission('product')
def variant_delete(product_id, variant_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 使用多個獨立 cursor 避免 unread result
        cursor1 = conn.cursor()
        cursor1.execute("UPDATE sku SET is_deleted = 1, is_active = 0 WHERE variant_id = %s", (variant_id,))
        cursor1.close()
        
        cursor2 = conn.cursor()
        cursor2.execute("UPDATE variant SET is_deleted = 1, is_active = 0 WHERE id = %s AND product_id = %s", (variant_id, product_id))
        rowcount = cursor2.rowcount
        cursor2.close()
        
        conn.commit()
        
        if rowcount == 0:
            flash("刪除失敗：找不到對應記錄")
        else:
            flash("款式已成功軟刪除")
    except Exception as e:
        conn.rollback()
        flash(f"刪除款式失敗: {str(e)}")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('staff.product.variant_list', product_id=product_id))


@product_bp.route('/sku/delete/<int:sku_id>', methods=['POST'])
@require_permission('product')
def sku_delete(sku_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT variant_id FROM sku WHERE id = %s", (sku_id,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        return redirect(url_for('staff.product.product_list'))
    variant_id = result['variant_id']
    cursor.execute("SELECT product_id FROM variant WHERE id = %s", (variant_id,))
    product_id = cursor.fetchone()['product_id']
    
    try:
        # 獨立刪除 SKU 改為軟刪除
        cursor.execute("UPDATE sku SET is_deleted = 1, is_active = 0 WHERE id = %s", (sku_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"刪除失敗: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.product.variant_list', product_id=product_id))


# ====== 新增：後台潛力商品排行榜 (購物車/願望清單分析) ======
@product_bp.route('/analytics/hot-items')
@require_permission('product') # 為了讓你們目前開發順暢，先綁定 product 權限，後續可依需求改為 'statistic'
def hot_items_analytics():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 撈出尚未下架的商品，並統計它們在 wishlist 和 cart 的熱度
    query = """
        SELECT 
            p.id, 
            p.name, 
            c.name as category_name,
            (SELECT COUNT(*) FROM wishlist_item wi WHERE wi.product_id = p.id) as wishlist_count,
            COALESCE((
                SELECT SUM(ci.qty) 
                FROM cart_item ci 
                JOIN sku s ON ci.sku_id = s.id 
                JOIN variant v ON s.variant_id = v.id 
                WHERE v.product_id = p.id
            ), 0) as cart_qty
        FROM product p
        LEFT JOIN category c ON p.category_id = c.id
        WHERE p.is_deleted = 0
        ORDER BY (wishlist_count + cart_qty) DESC
        LIMIT 10;
    """
    
    cursor.execute(query)
    hot_items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # 這個路由對應的 HTML 檔案需要你們後續建立 (staff/analytics_hot_items.html)
    return render_template('staff/analytics_hot_items.html', items=hot_items)