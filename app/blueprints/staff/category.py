from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import get_db_connection
from .permission import require_permission
from app.models.category_model import CategoryModel

category_bp = Blueprint('category', __name__)

@category_bp.route('/')
@require_permission('product')
def category_list():
    categories = CategoryModel.get_all()
    return render_template('staff/category_list.html', categories=categories)

@category_bp.route('/add', methods=['POST'])
@require_permission('product')
def category_add():
    name = request.form.get('name', '').strip()
    if not name:
        flash("分類名稱不能為空")
        return redirect(url_for('staff.category.category_list'))
    if len(name) > 30:
        flash("分類名稱長度不能超過 30 個字元")
        return redirect(url_for('staff.category.category_list'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 檢查重複名稱 (不包含已刪除的)
    cursor.execute("SELECT id FROM category WHERE name = %s AND is_deleted = 0", (name,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        flash("此分類名稱已存在")
        return redirect(url_for('staff.category.category_list'))

    try:
        cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES (%s, NOW(), NOW())", (name,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"新增失敗: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.category.category_list'))

@category_bp.route('/edit/<int:id>', methods=['POST'])
@require_permission('product')
def category_edit(id):
    name = request.form.get('name', '').strip()
    if not name:
        flash("分類名稱不能為空")
        return redirect(url_for('staff.category.category_list'))
    if len(name) > 30:
        flash("分類名稱長度不能超過 30 個字元")
        return redirect(url_for('staff.category.category_list'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 檢查重複名稱 (排除自己，不包含已刪除的)
    cursor.execute("SELECT id FROM category WHERE name = %s AND id != %s AND is_deleted = 0", (name, id))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        flash("此分類名稱已與其他分類重複")
        return redirect(url_for('staff.category.category_list'))

    try:
        cursor.execute("UPDATE category SET name=%s, updated_at=NOW() WHERE id=%s", (name, id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash(f"修改失敗: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.category.category_list'))

@category_bp.route('/delete/<int:id>', methods=['POST'])
@require_permission('product')
def category_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 檢查是否有未刪除的產品屬於此分類
        cursor.execute("SELECT COUNT(*) FROM product WHERE category_id = %s AND is_deleted = 0", (id,))
        count = cursor.fetchone()[0]
        if count > 0:
            flash("此分類下尚有商品，無法刪除")
        else:
            CategoryModel.soft_delete(id)
            flash("分類已刪除")
    except Exception as e:
        flash(f"刪除失敗: {str(e)}")
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.category.category_list'))
