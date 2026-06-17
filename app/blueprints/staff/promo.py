from flask import Blueprint, session, request, redirect, render_template, url_for, flash
from app.db import get_db_connection
from datetime import datetime
from .permission import require_permission

promo_bp = Blueprint('promo', __name__)

def validate_discount(discount_type, discount_value):
    if discount_type == 'subtotal_discount':
        if not (0 <= discount_value <= 100):
            return "小計打折 (百分比) 必須介於 0 到 100 之間"
    elif discount_type in ['subtotal_deduction', 'shipping_deduction']:
        if discount_value < 0:
            return "折抵金額不能為負數"
        if discount_value > 1000000: # 增加一個合理的上限
            return "折抵金額過大"
    elif discount_type == 'free_shipping':
        if discount_value != 0:
            return "免運費折扣值應設為 0"
    return None

@promo_bp.route('/list')
@require_permission('promo')
def promo_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM promo_code WHERE is_deleted = 0")
    promos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('staff/promo_list.html', promos=promos)

@promo_bp.route('/add', methods=['GET', 'POST'])
@require_permission('promo')
def promo_add():
    form_data = {}
        
    if request.method == 'POST':
        form_data = request.form.to_dict()
        code = request.form.get('code')
        description = request.form.get('description')
        discount_type = request.form.get('discount_type')
        
        # 強制欄位驗證
        if not all([code, description, discount_type]):
            flash("所有欄位均為必填")
            return render_template('staff/promo_add.html', form_data=form_data)
        
        # Input Validation (🌟 新增 per_user_limit 與 is_public 取值與驗證)
        try:
            discount_value = float(request.form.get('discount_value', 0))
            usage_limit = int(request.form.get('usage_limit', 0))
            per_user_limit = int(request.form.get('per_user_limit', 1))
            min_order_amount = float(request.form.get('min_order_amount', 0))
            is_public = int(request.form.get('is_public', 0))
        except ValueError:
            flash("折扣值、使用限制、金額等欄位必須為有效數字")
            return render_template('staff/promo_add.html', form_data=form_data)
        
        # Validation
        error = validate_discount(discount_type, discount_value)
        if error:
            flash(error)
            return render_template('staff/promo_add.html', form_data=form_data)
            
        if min_order_amount < 0 or usage_limit < 0 or per_user_limit < 0:
            flash("最低訂單金額或使用限制不能為負數")
            return render_template('staff/promo_add.html', form_data=form_data)
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # 檢查是否已存在 (且未被軟刪除)
        cursor.execute("SELECT id FROM promo_code WHERE code = %s AND is_deleted = 0", (code,))
        if cursor.fetchone():
            flash("此代碼已存在")
            cursor.close()
            conn.close()
            return render_template('staff/promo_add.html', form_data=form_data)
            
        start_at = request.form['start_at'] if request.form['start_at'] else None
        end_at = request.form['end_at'] if request.form['end_at'] else None
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 🌟 更新 SQL 加入 per_user_limit 和 is_public
        sql = """INSERT INTO promo_code (code, description, discount_type, discount_value, usage_limit, per_user_limit, min_order_amount, is_public, start_at, end_at, is_deleted, created_at, updated_at)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s)"""
        cursor.execute(sql, (code, description, discount_type, discount_value, usage_limit, per_user_limit, min_order_amount, is_public, start_at, end_at, now, now))
        conn.commit()
        cursor.close()
        conn.close()
        flash("折扣碼新增成功")
        return redirect(url_for('staff.promo.promo_list'))
        
    return render_template('staff/promo_add.html', form_data=form_data)

@promo_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@require_permission('promo')
def promo_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        code = request.form['code']
        description = request.form['description']
        discount_type = request.form['discount_type']
        
        # Input Validation (🌟 新增 per_user_limit 與 is_public 取值與驗證)
        try:
            discount_value = float(request.form['discount_value'])
            usage_limit = int(request.form.get('usage_limit', 0))
            per_user_limit = int(request.form.get('per_user_limit', 1))
            min_order_amount = float(request.form.get('min_order_amount', 0))
            is_public = int(request.form.get('is_public', 0))
        except ValueError:
            flash("折扣值、使用限制、金額等欄位必須為有效數字")
            return redirect(url_for('staff.promo.promo_edit', id=id))
        
        # Validation
        error = validate_discount(discount_type, discount_value)
        if error:
            flash(error)
            return redirect(url_for('staff.promo.promo_edit', id=id))
            
        if min_order_amount < 0 or usage_limit < 0 or per_user_limit < 0:
            flash("最低訂單金額或使用限制不能為負數")
            return redirect(url_for('staff.promo.promo_edit', id=id))
            
        start_at = request.form['start_at'] if request.form['start_at'] else None
        end_at = request.form['end_at'] if request.form['end_at'] else None
        
        # 🌟 更新 SQL 加入 per_user_limit 和 is_public
        sql = """UPDATE promo_code SET code=%s, description=%s, discount_type=%s, discount_value=%s, 
                 usage_limit=%s, per_user_limit=%s, min_order_amount=%s, is_public=%s, start_at=%s, end_at=%s, updated_at=%s WHERE id=%s"""
        cursor.execute(sql, (code, description, discount_type, discount_value, usage_limit, per_user_limit, min_order_amount, is_public, start_at, end_at, datetime.now(), id))
        conn.commit()
        flash("折扣碼更新成功")
        cursor.close()
        conn.close()
        return redirect(url_for('staff.promo.promo_list'))
        
    cursor.execute("SELECT * FROM promo_code WHERE id = %s", (id,))
    promo = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('staff/promo_edit.html', promo=promo)

@promo_bp.route('/delete/<int:id>', methods=['POST'])
@require_permission('promo')
def promo_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # 改用軟刪除
    cursor.execute("UPDATE promo_code SET is_deleted = 1 WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("折扣碼已刪除")
    return redirect(url_for('staff.promo.promo_list'))