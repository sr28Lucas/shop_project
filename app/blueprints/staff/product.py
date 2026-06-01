from flask import Blueprint, session, request, redirect, render_template, url_for, flash 
from werkzeug.utils import secure_filename
from app.db import get_db_connection
from datetime import datetime
from app.config import config
import os


product_bp = Blueprint('product', __name__) #建立藍圖


@product_bp.route('/list')
def product_list():
    #從URL獲取篩選範圍
    category_id = request.args.get('category_id')
    is_active = request.args.get('is_active')
    
    query = """
    SELECT p.*, c.name as category_name
    FROM product p 
    LEFT JOIN category c ON p.category_id = c.id
    """

    #篩選參數
    params = []
    conditions = []

    if category_id:
        conditions.append("p.category_id = %s")
        params.append(category_id)
    if is_active:
        conditions.append("p.is_active = %s")
        params.append(is_active)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    #連接並執行
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(query, params)
    products = cursor.fetchall()
    
    # 獲取所有分類，移除 is_deleted 檢查
    cursor.execute("SELECT * FROM category")
    categories = cursor.fetchall()

    return render_template('staff/product_list.html', products=products, categories=categories)


@product_bp.route('/add', methods=['GET', 'POST'])
def product_add():
    if request.method == 'POST':
        #從表單獲取商品資料
        name = request.form['name']
        category_id = request.form.get('category_id')
        description = request.form.get('description')
        files = request.files.getlist('images')

        if not category_id:
            return "商品必須選擇分類", 400

        #連接資料庫
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 檢查重複名稱，移除 is_deleted 檢查
        cursor.execute("SELECT id FROM product WHERE name = %s", (name,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return "商品名稱已存在", 400

        #如果upload就創建資料夾
        if not os.path.exists(config.UPLOAD_FOLDER):
            os.makedirs(config.UPLOAD_FOLDER)

        try:
            # 1. 插入商品主檔
            cursor.execute("""
                INSERT INTO product (category_id, name, description, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, 0, NOW(), NOW())
            """, (category_id, name, description))
            
            product_id = cursor.lastrowid

            # 2. 處理圖片
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for index, file in enumerate(files):
                if file:
                    # 先插入圖片紀錄
                    cursor.execute("""
                        INSERT INTO image (product_id, filename, sort_order, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (product_id, "", index, now, now)) 
                    
                    image_id = cursor.lastrowid
                    
                    # 重新命名
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"{product_id}_{image_id}{ext}"
                    
                    # 儲存檔案
                    upload_path = os.path.join(config.UPLOAD_FOLDER, filename)
                    file.save(upload_path)
                    
                    # 更新資料庫中的 filename
                    cursor.execute("UPDATE image SET filename = %s WHERE id = %s", (filename, image_id))

            conn.commit()
            return "OK", 200 # 回應 fetch

        #錯誤回滾
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return "Internal Server Error", 500
        finally:
            cursor.close()
            conn.close()

    #斷開資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM category")
    categories = cursor.fetchall()
    return render_template('staff/product_add.html', categories = categories)





@product_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def product_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        category_id = request.form.get('category_id')
        description = request.form.get('description')
        
        if not category_id:
            cursor.close()
            conn.close()
            return "商品必須選擇分類", 400

        # 取得排序與刪除資訊
        image_order = request.form.get('image_order').split(',')
        deleted_ids = request.form.get('deleted_ids')
        new_files = request.files.getlist('images')

        # 檢查重複名稱 (排除自己)，移除 is_deleted 檢查
        cursor.execute("SELECT id FROM product WHERE name = %s AND id != %s", (name, id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return "商品名稱已存在", 400

        try:
            # 更新產品主檔
            cursor.execute("""
                UPDATE product 
                SET category_id=%s, name=%s, description=%s, updated_at=NOW()
                WHERE id=%s
            """, (category_id, name, description, id))

            # 處理圖片刪除
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

            # 處理排序與新圖片
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

    # GET 邏輯
    cursor.execute("SELECT * FROM product WHERE id = %s", (id,))
    product = cursor.fetchone()
    
    cursor.execute("SELECT * FROM image WHERE product_id = %s ORDER BY sort_order", (id,))
    images = cursor.fetchall()
    
    cursor.execute("SELECT id, name FROM category")
    categories = cursor.fetchall()
    
    conn.close()
    return render_template('staff/product_edit.html', product=product, images=images, categories=categories)


@product_bp.route('/bulk_update_status', methods=['POST'])
def bulk_update_status():
    product_ids = request.form.getlist('product_ids')
    action = request.form.get('action')
    
    if not product_ids:
        flash("請先勾選商品")
        return redirect(url_for('staff.product.product_list'))
        
    is_active = 1 if action == 'on' else 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        format_strings = ','.join(['%s'] * len(product_ids))
        cursor.execute(f"UPDATE product SET is_active = %s, updated_at = NOW() WHERE id IN ({format_strings})", [is_active] + product_ids)
        conn.commit()
        flash(f"已成功將 {cursor.rowcount} 個商品{'上架' if is_active else '下架'}")
    except Exception as e:
        conn.rollback()
        flash(f"批次更新失敗: {e}")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('staff.product.product_list'))


@product_bp.route('/delete/<int:id>', methods=['POST'])
def product_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 硬刪除，移除軟刪除相關更新
        cursor.execute("DELETE FROM product WHERE id = %s", (id,))
        # 相關 SKU 應該也要刪除，因為使用了 foreign key 應設定 cascade，或在此處手動刪除相關 records
        cursor.execute("DELETE FROM sku WHERE variant_id IN (SELECT id FROM variant WHERE product_id = %s)", (id,))
        cursor.execute("DELETE FROM variant WHERE product_id = %s", (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error deleting product: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.product.product_list'))


@product_bp.route('/<int:product_id>/variant')
def variant_list(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name FROM product WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.execute("SELECT * FROM variant WHERE product_id = %s", (product_id,))
    variants = cursor.fetchall()
    cursor.execute("""
        SELECT s.*, v.color 
        FROM sku s
        JOIN variant v ON s.variant_id = v.id
        WHERE v.product_id = %s
    """, (product_id,))
    skus = cursor.fetchall()
    for v in variants:
        v['skus'] = [s for s in skus if s['variant_id'] == v['id']]
    cursor.close()
    conn.close()
    return render_template("staff/variant_list.html", product_id=product_id, product_name=product['name'] if product else "未知商品", variants=variants)

@product_bp.route('/<int:product_id>/variant/add', methods=['GET', 'POST'])
def variant_add(product_id):
    if request.method == 'POST':
        color = request.form.get('color')
        is_active = 1 if request.form.get('variant_is_active') else 0
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
            # 1. 建立變體
            cursor.execute("INSERT INTO variant (product_id, color, is_active, created_at, updated_at) VALUES (%s, %s, %s, NOW(), NOW())", (product_id, color, is_active))
            variant_id = cursor.lastrowid
            
            # 2. 處理圖片
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
            
            # 3. 處理 SKU
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for i in range(len(sizes)):
                sku_code = sku_codes[i]
                size = sizes[i]
                price = float(prices[i])
                cost = float(costs[i])
                stock = int(stocks[i])
                is_sku_active = 1 if str(i) in active_indices else 0
                
                cursor.execute("""
                    INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        
        # 圖片處理
        variant_image_file = request.files.get('variant_image')
        delete_image = request.form.get('delete_image') == '1'
        
        try:
            # 1. 更新變體基本資料
            cursor.execute("UPDATE variant SET color = %s, is_active = %s, updated_at = NOW() WHERE id = %s", (color, variant_is_active, variant_id))
            
            # 2. 處理 SKU
            submitted_sku_ids = []
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for i in range(len(sizes)):
                s_id = int(sku_ids[i]) if (i < len(sku_ids) and sku_ids[i]) else None
                sku_code = sku_codes[i]
                size = sizes[i]
                price = float(prices[i])
                cost = float(costs[i])
                stock = int(stocks[i])
                is_active = 1 if str(i) in active_indices else 0
                
                if s_id: 
                    cursor.execute("""
                        UPDATE sku SET sku_code=%s, size=%s, price=%s, cost=%s, stock=%s, is_active=%s, updated_at=%s
                        WHERE id=%s AND variant_id=%s
                    """, (sku_code, size, price, cost, stock, is_active, now, s_id, variant_id))
                    submitted_sku_ids.append(s_id)
                else: 
                    cursor.execute("""
                        INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (variant_id, sku_code, size, price, cost, stock, is_active, now, now))
                    submitted_sku_ids.append(cursor.lastrowid)
            
            if submitted_sku_ids:
                format_strings = ','.join(['%s'] * len(submitted_sku_ids))
                cursor.execute(f"DELETE FROM sku WHERE variant_id = %s AND id NOT IN ({format_strings})", [variant_id] + submitted_sku_ids)
            else:
                cursor.execute("DELETE FROM sku WHERE variant_id = %s", (variant_id,))

            # 3. 處理圖片
            if delete_image or variant_image_file:
                # 刪除舊圖
                cursor.execute("SELECT id, filename FROM image WHERE variant_id = %s", (variant_id,))
                old_imgs = cursor.fetchall()
                for img in old_imgs:
                    file_path = os.path.join(config.UPLOAD_FOLDER, img['filename'])
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    cursor.execute("DELETE FROM image WHERE id = %s", (img['id'],))

            if variant_image_file:
                # 插入新圖
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
        
    cursor.execute("SELECT * FROM sku WHERE variant_id = %s", (variant_id,))
    skus = cursor.fetchall()
    cursor.execute("SELECT * FROM image WHERE variant_id = %s LIMIT 1", (variant_id,))
    image = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("staff/variant_edit.html", variant=variant, skus=skus, product_id=product_id, image=image)





@product_bp.route('/sku/delete/<int:sku_id>', methods=['POST'])
def sku_delete(sku_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT variant_id FROM sku WHERE id = %s", (sku_id,))
    variant_id = cursor.fetchone()['variant_id']
    cursor.execute("SELECT product_id FROM variant WHERE id = %s", (variant_id,))
    product_id = cursor.fetchone()['product_id']
    
    try:
        cursor.execute("DELETE FROM sku WHERE id = %s", (sku_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"刪除失敗: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.product.variant_list', product_id=product_id))
