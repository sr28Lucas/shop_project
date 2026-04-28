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

    return render_template('admin/product_list.html', products=products, categories=categories)


@product_bp.route('/add', methods=['GET', 'POST'])
def product_add():
    if request.method == 'POST':
        # 1. 獲取表單資料
        name = request.form['name']
        price = request.form['price']
        stock = request.form['stock']
        description = request.form['description']
        status = 'inactive'
        recommended = 0
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        files = request.files.getlist('images') # 取得多張圖片
        

        #寫入
        try:
            #連接資料庫
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                           INSERT INTO product(name, price, stock, description, status, recommended, created_at, update_at)
                           VALUES (%s, %d, %d, %s, %s, %d, %s, %s)
                           """, (name, price, stock, description, status, recommended, now, now))
            
            product_id = cursor.lastrowid()

            # 3. 處理圖片上傳
            for index, file in enumerate(files):
                if file:
                    filename = secure_filename(f"{product_id}_{file.filename}")
                    file.save(os.path.join(config['UPLOAD_FOLDER'], filename))
                    
                    # 寫入 image 表
                    cursor.execute("INSERT INTO image (product_id, url, is_primary, sort_order) VALUES (%s, %s, %s,%d)"\
                                   (product_id, filename, index))
            conn.commit()

            return redirect(url_for('admin.product_list'))
        
        except Exception as e:
            conn.rollback()
            for index, file in enumerate(files):
                filename = secure_filename(f"{product_id}_{file.filename}")
                file_path = os.path.exists(os.path.join(config['UPLOAD_FOLDER']), filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        pass
        finally:
            cursor.close()
            conn.close()

        return "<script>alert('商品新增成功'); window.location.href = '/admin/product/list';</script>"

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM category")
    categories = cursor.fetchall()
    return render_template('admin/product_add.html', categories = categories)


