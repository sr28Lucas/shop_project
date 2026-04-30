from flask import Blueprint, session, request, redirect, render_template, url_for 
from werkzeug.utils import secure_filename
from app.db import get_db_connection
from datetime import datetime
from app.config import config
import os


product_bp = Blueprint('product', __name__) #建立藍圖


@product_bp.route('/list')
def product_list():
    category_id = request.args.get('category_id')
    status = request.args.get('status')
    
    query = "SELECT p.*, c.name as category_name FROM product p JOIN category c ON p.category_id = c.id WHERE p.is_deleted = 0"
    params = []
    
    if category_id:
        query += " AND p.category_id = %s"
        params.append(category_id)
    if status:
        query += " AND p.status = %s"
        params.append(status)
    

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




@product_bp.route('/edit', methods=['GET', 'POST'])
def product_edit():
    return 'pass', 200
