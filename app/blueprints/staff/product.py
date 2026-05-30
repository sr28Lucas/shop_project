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
    SELECT p.*, c.name as category_name,
           (SELECT SUM(stock) FROM sku WHERE product_id = p.id AND is_deleted = 0) as total_stock
    FROM product p 
    LEFT JOIN category c ON p.category_id = c.id WHERE p.is_deleted = 0
    """

    #篩選參數
    params = []

    if category_id:
        query += " AND p.category_id = %s"
        params.append(category_id)
    if is_active:
        query += " AND p.is_active = %s"
        params.append(is_active)
    
    #連接並執行
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)



    cursor.execute(query, params)
    products = cursor.fetchall()
    cursor.execute("SELECT * FROM category WHERE is_deleted = 0")
    categories = cursor.fetchall()

    return render_template('staff/product_list.html', products=products, categories=categories)


@product_bp.route('/add', methods=['GET', 'POST'])
def product_add():
    if request.method == 'POST':
        #從表單獲取商品資料
        name = request.form['name']
        category_id = request.form.get('category_id') or None
        description = request.form.get('description')
        files = request.files.getlist('images')

        #連接資料庫
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 檢查重複名稱
        cursor.execute("SELECT id FROM product WHERE name = %s AND is_deleted = 0", (name,))
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

            # 2. 處理圖片 (此時 files 的順序已經是前端拖拽後的順序)
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for index, file in enumerate(files):
                if file:
                    # 先插入圖片紀錄以取得 image_id
                    cursor.execute("""
                        INSERT INTO image (product_id, filename, sort_order, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (product_id, "", index, now, now)) # 暫時給空 filename
                    
                    image_id = cursor.lastrowid
                    
                    # 重新命名：product_id_image_id.副檔名
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
    cursor.execute("SELECT id, name FROM category WHERE is_deleted = 0")
    categories = cursor.fetchall()
    return render_template('staff/product_add.html', categories = categories)




@product_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def product_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        category_id = request.form.get('category_id') or None
        description = request.form.get('description')
        
        # 取得排序與刪除資訊 (由 JS 傳來的 JSON 字串)
        image_order = request.form.get('image_order').split(',') # 例如: "old_10,old_12,new_0"
        deleted_ids = request.form.get('deleted_ids') # 例如: "11,13"
        new_files = request.files.getlist('images')

        # 檢查重複名稱 (排除自己)
        cursor.execute("SELECT id FROM product WHERE name = %s AND is_deleted = 0 AND id != %s", (name, id))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return "商品名稱已存在", 400

        try:
            # 1. 更新產品主檔
            cursor.execute("""
                UPDATE product 
                SET category_id=%s, name=%s, description=%s, updated_at=NOW()
                WHERE id=%s
            """, (category_id, name, description, id))

            # 2. 處理刪除
            if deleted_ids:
                id_list = [int(i) for i in deleted_ids.split(',') if i]
                for d_id in id_list:
                    # 先找檔名以便刪除實體檔案
                    cursor.execute("SELECT filename FROM image WHERE id=%s", (d_id,))
                    img_data = cursor.fetchone()
                    if img_data:
                        file_path = os.path.join(config.UPLOAD_FOLDER, img_data['filename'])
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    # 刪除資料庫紀錄
                    cursor.execute("DELETE FROM image WHERE id=%s", (d_id,))

            # 3. 處理排序與新圖片
            # 我們按照 image_order 的順序來處理
            new_file_index = 0
            for index, item_tag in enumerate(image_order):
                if not item_tag: continue
                
                if item_tag.startswith('old_'):
                    # 更新舊圖片的排序
                    old_id = item_tag.split('_')[1]
                    cursor.execute("UPDATE image SET sort_order=%s WHERE id=%s", (index, old_id))
                
                elif item_tag.startswith('new_'):
                    # 處理新圖片
                    file = new_files[new_file_index]
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 插入空資料取 ID
                    cursor.execute("""
                        INSERT INTO image (product_id, filename, sort_order, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (id, "", index, now, now))
                    
                    new_img_id = cursor.lastrowid
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"{id}_{new_img_id}{ext}"
                    
                    # 儲存與更新 URL
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

    # GET 邏輯：讀取資料
    cursor.execute("SELECT * FROM product WHERE id = %s", (id,))
    product = cursor.fetchone()
    
    cursor.execute("SELECT * FROM image WHERE product_id = %s ORDER BY sort_order", (id,))
    images = cursor.fetchall()
    
    cursor.execute("SELECT id, name FROM category WHERE is_deleted = 0")
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
        # 使用 IN 子句批次更新
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
        # Soft delete product
        cursor.execute("UPDATE product SET is_deleted = 1, updated_at = NOW() WHERE id = %s", (id,))
        # Soft delete related SKUs
        cursor.execute("UPDATE sku SET is_deleted = 1, updated_at = NOW() WHERE product_id = %s", (id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error deleting product: {e}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.product.product_list'))


@product_bp.route('/<int:product_id>/sku')
def sku_list(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 獲取產品名稱
    cursor.execute("SELECT name FROM product WHERE id = %s", (product_id,))
    product = cursor.fetchone()
    
    # 獲取 SKU 列表
    cursor.execute("SELECT * FROM sku WHERE product_id = %s AND is_deleted = 0", (product_id,))
    skus = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template("staff/sku_list.html", product_id=product_id, product_name=product['name'] if product else "未知商品", skus=skus)


@product_bp.route('/<int:product_id>/sku/add', methods=['GET', 'POST'])
def sku_add(product_id):
    if request.method == 'POST':
        sku_code = request.form.get('sku_code')
        size = request.form.get('size')
        color = request.form.get('color')
        price = request.form.get('price')
        cost = request.form.get('cost')
        stock = request.form.get('stock')
        files = request.files.getlist('images')

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO sku (product_id, sku_code, size, color, price, cost, stock, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (product_id, sku_code, size, color, price, cost, stock))
            sku_id = cursor.lastrowid

            # 處理圖片
            for index, file in enumerate(files):
                if file:
                    cursor.execute("""
                        INSERT INTO image (product_id, sku_id, image_type, filename, sort_order, created_at, updated_at)
                        VALUES (%s, %s, 'sku', '', %s, NOW(), NOW())
                    """, (product_id, sku_id, index))
                    image_id = cursor.lastrowid
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"sku_{sku_id}_{image_id}{ext}"
                    file.save(os.path.join(config.UPLOAD_FOLDER, filename))
                    cursor.execute("UPDATE image SET filename = %s WHERE id = %s", (filename, image_id))
            
            conn.commit()
            return redirect(url_for('staff.product.sku_list', product_id=product_id))
        except Exception as e:
            conn.rollback()
            flash(f"新增失敗: {str(e)}")
        finally:
            cursor.close()
            conn.close()

    return render_template('staff/sku_add.html', product_id=product_id)


@product_bp.route('/<int:product_id>/sku/edit/<int:sku_id>', methods=['GET', 'POST'])
def sku_edit(product_id, sku_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == "POST":
        sku_code = request.form.get("sku_code")
        size = request.form.get("size")
        color = request.form.get("color")
        price = request.form.get("price")
        cost = request.form.get("cost")
        stock = request.form.get("stock")
        is_active = request.form.get("is_active")
        
        # 圖片處理 (簡化版：僅新增，實際可參考 product_edit 完整版)
        files = request.files.getlist('images')

        try: 
            cursor.execute("""
                UPDATE sku 
                SET sku_code=%s, size=%s, color=%s, price=%s, cost=%s, stock=%s, is_active=%s, updated_at=NOW()
                WHERE id=%s
            """, (sku_code, size, color, price, cost, stock, is_active, sku_id))
            
            for index, file in enumerate(files):
                if file:
                    cursor.execute("""
                        INSERT INTO image (product_id, sku_id, image_type, filename, sort_order, created_at, updated_at)
                        VALUES (%s, %s, 'sku', '', %s, NOW(), NOW())
                    """, (product_id, sku_id, index))
                    image_id = cursor.lastrowid
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"sku_{sku_id}_{image_id}{ext}"
                    file.save(os.path.join(config.UPLOAD_FOLDER, filename))
                    cursor.execute("UPDATE image SET filename = %s WHERE id = %s", (filename, image_id))

            conn.commit()
            return redirect(url_for('staff.product.sku_list', product_id=product_id))
        except Exception as e:
            conn.rollback()
            flash(f"修改失敗: {str(e)}")
        finally:
            cursor.close()
            conn.close()
        
    cursor.execute("SELECT * FROM sku WHERE id = %s", (sku_id,))
    sku = cursor.fetchone()
    cursor.execute("SELECT * FROM image WHERE sku_id = %s ORDER BY sort_order", (sku_id,))
    images = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("staff/sku_edit.html", product_id=product_id, sku=sku, images=images)


@product_bp.route('/<int:product_id>/sku/delete/<int:sku_id>', methods=['POST'])
def sku_delete(product_id, sku_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE sku SET is_deleted = 1, updated_at = NOW() WHERE id = %s", (sku_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"刪除失敗: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.product.sku_list', product_id=product_id))