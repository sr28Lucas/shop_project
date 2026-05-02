from flask import Blueprint, session, request, redirect, render_template, url_for 
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
    JOIN category c ON p.category_id = c.id WHERE p.is_deleted = 0
    """

    #篩選參數
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
    cursor.execute("SELECT * FROM category")
    categories = cursor.fetchall()

    return render_template('staff/product_list.html', products=products, categories=categories)


@product_bp.route('/add', methods=['GET', 'POST'])
def product_add():
    if request.method == 'POST':
        name = request.form['name']
        category_id = request.form.get('category_id')
        description = request.form.get('description')
        files = request.files.getlist('images')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if not os.path.exists(config.UPLOAD_FOLDER):
            os.makedirs(config.UPLOAD_FOLDER)

        try:
            # 1. 插入商品主檔
            cursor.execute("""
                INSERT INTO product (category_id, name, description, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, 1, NOW(), NOW())
            """, (category_id, name, description))
            
            product_id = cursor.lastrowid

            # 2. 處理圖片 (此時 files 的順序已經是前端拖拽後的順序)
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for index, file in enumerate(files):
                if file:
                    # 先插入圖片紀錄以取得 image_id
                    cursor.execute("""
                        INSERT INTO image (product_id, url, sort_order, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (product_id, "", index, now, now)) # 暫時給空 url
                    
                    image_id = cursor.lastrowid
                    
                    # 重新命名：product_id_image_id.副檔名
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"{product_id}_{image_id}{ext}"
                    
                    # 儲存檔案
                    upload_path = os.path.join(config.UPLOAD_FOLDER, filename)
                    file.save(upload_path)
                    
                    # 更新資料庫中的 url
                    cursor.execute("UPDATE image SET url = %s WHERE id = %s", (filename, image_id))

            conn.commit()
            return "OK", 200 # 回應 fetch

        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            return "Internal Server Error", 500
        finally:
            cursor.close()
            conn.close()

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
        
        # 取得排序與刪除資訊 (由 JS 傳來的 JSON 字串)
        image_order = request.form.get('image_order').split(',') # 例如: "old_10,old_12,new_0"
        deleted_ids = request.form.get('deleted_ids') # 例如: "11,13"
        new_files = request.files.getlist('images')

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
                    cursor.execute("SELECT url FROM image WHERE id=%s", (d_id,))
                    img_data = cursor.fetchone()
                    if img_data:
                        file_path = os.path.join(config.UPLOAD_FOLDER, img_data['url'])
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
                        INSERT INTO image (product_id, url, sort_order, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (id, "", index, now, now))
                    
                    new_img_id = cursor.lastrowid
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"{id}_{new_img_id}{ext}"
                    
                    # 儲存與更新 URL
                    file.save(os.path.join(config.UPLOAD_FOLDER, filename))
                    cursor.execute("UPDATE image SET url = %s WHERE id = %s", (filename, new_img_id))
                    
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
    
    cursor.execute("SELECT id, name FROM category")
    categories = cursor.fetchall()
    
    conn.close()
    return render_template('staff/product_edit.html', product=product, images=images, categories=categories)
