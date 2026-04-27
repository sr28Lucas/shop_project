from flask import Blueprint, session, redirect, render_template, url_for, request
from app.db import get_db_connection


product_bp = Blueprint('product', __name__, template_folder = '../templates/admin') #建立藍圖


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
        files = request.files.getlist('images') # 取得多張圖片
        
        try:
            # 2. 寫入產品表
            product_id = db.execute(
                "INSERT INTO product (name, price, category_id, status) VALUES (%s, %s, %s, %s)",
                (name, price, request.form['category_id'], 'unlisted')
            ).lastrowid
            
            # 3. 處理圖片上傳
            for index, file in enumerate(files):
                if file:
                    filename = secure_filename(f"{product_id}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    
                    # 寫入 image 表
                    db.execute(
                        "INSERT INTO image (product_id, url, is_primary) VALUES (%s, %s, %s)",
                        (product_id, filename, 1 if index == 0 else 0)
                    )
            db.commit()
            return redirect(url_for('admin.product_list'))
        except Exception as e:
            db.rollback()
            # 可以在此加入刪除已存檔案的邏輯
            return "存檔失敗", 500

    categories = db.execute("SELECT * FROM category").fetchall()
    return render_template('admin/product_form.html', categories=categories, product=None)


