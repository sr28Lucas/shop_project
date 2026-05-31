from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.db import get_db_connection
from app.extensions import bcrypt
from datetime import datetime

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/edit', methods=['GET', 'POST'])
def edit():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        region = request.form.get('region')
        locality = request.form.get('locality')
        
        # 後端驗證
        if len(name) < 1 or len(name) > 30:
            flash("姓名長度需在 1-30 字元之間。", "error")
            return redirect(url_for('customer.profile.edit'))
        if phone and (len(phone) < 8 or len(phone) > 20):
            flash("電話長度需在 8-20 碼之間。", "error")
            return redirect(url_for('customer.profile.edit'))
        if address and (len(address) < 5 or len(address) > 100):
            flash("地址長度需在 5-100 字元之間。", "error")
            return redirect(url_for('customer.profile.edit'))

        try:
            sql = """UPDATE customer 
                     SET name = %s, phone = %s, region = %s, locality = %s, address = %s, updated_at = NOW() 
                     WHERE id = %s"""
            # 處理空字串轉換為 NULL
            cursor.execute(sql, (name, phone or None, region or None, locality or None, address or None, session['customer_id']))
            conn.commit()
            flash("資料更新成功！", "success")
            return redirect(url_for('customer.profile.edit'))
        except Exception as e:
            conn.rollback()
            flash(f"更新失敗: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()
            
    cursor.execute("SELECT * FROM customer WHERE id = %s", (session['customer_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('customer/profile_edit.html', user=user)

@profile_bp.route('/password', methods=['GET', 'POST'])
def change_password():
    if 'customer_id' not in session:
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash("新密碼與確認密碼不一致", "error")
            return redirect(url_for('customer.profile.change_password'))
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password FROM customer WHERE id = %s", (session['customer_id'],))
        user = cursor.fetchone()
        
        if user and bcrypt.check_password_hash(user['password'], old_password):
            hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
            cursor.execute("UPDATE customer SET password = %s, updated_at = NOW() WHERE id = %s", 
                           (hashed_pw, session['customer_id']))
            conn.commit()
            cursor.close()
            conn.close()
            flash("密碼修改成功！", "success")
            return redirect(url_for('customer.center'))
        else:
            cursor.close()
            conn.close()
            flash("原密碼輸入錯誤", "error")
            return redirect(url_for('customer.profile.change_password'))
            
    return render_template('customer/password_edit.html')
