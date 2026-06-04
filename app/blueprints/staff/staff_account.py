from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from datetime import datetime
from app.extensions import bcrypt
from .permission import require_permission

staff_account_bp = Blueprint('staff_account', __name__)

@staff_account_bp.route('/list')
@require_permission('staff')
def staff_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.*, r.name as role_name 
        FROM staff s 
        LEFT JOIN role r ON s.role_id = r.id 
        ORDER BY s.id DESC
    """)
    staffs = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('staff/staff_list.html', staffs=staffs)

@staff_account_bp.route('/add', methods=['GET', 'POST'])
@require_permission('staff')
def staff_add():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role_id = request.form.get('role_id')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if password != password_confirm:
            flash('密碼與確認密碼不一致')
            return redirect(url_for('staff.staff_account.staff_list'))

        try:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute("""
                INSERT INTO staff (name, email, phone, role_id, password, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, role_id, hashed_password, datetime.now(), datetime.now()))
            conn.commit()
            flash('員工帳號新增成功')
        except Exception as e:
            conn.rollback()
            flash(f'新增失敗: {e}')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('staff.staff_account.staff_list'))

    cursor.execute("SELECT * FROM role")
    roles = cursor.fetchall()
    cursor.close()
    conn.close()
        
    return render_template('staff/staff_edit.html', staff=None, roles=roles)

@staff_account_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@require_permission('staff')
def staff_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM staff WHERE id = %s", (id,))
    staff = cursor.fetchone()
    
    if not staff:
        cursor.close()
        conn.close()
        flash('找不到員工')
        return redirect(url_for('staff.staff_account.staff_list'))

    if request.method == 'POST':
        # Root 帳號保護：禁止編輯
        if staff['email'] == 'root@root':
            flash('Root 帳號資料受保護，無法編輯。')
            return redirect(url_for('staff.staff_account.staff_list'))

        name = request.form.get('name')
        phone = request.form.get('phone')
        role_id = request.form.get('role_id')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        is_active = 1 if 'is_active' in request.form else 0
        
        if password and password != password_confirm:
            flash('密碼與確認密碼不一致')
            return redirect(url_for('staff.staff_account.staff_edit', id=id))

        try:
            if password:
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                cursor.execute("""
                    UPDATE staff 
                    SET name=%s, phone=%s, role_id=%s, password=%s, is_active=%s, updated_at=%s
                    WHERE id=%s
                """, (name, phone, role_id, hashed_password, is_active, datetime.now(), id))
            else:
                cursor.execute("""
                    UPDATE staff 
                    SET name=%s, phone=%s, role_id=%s, is_active=%s, updated_at=%s
                    WHERE id=%s
                """, (name, phone, role_id, is_active, datetime.now(), id))
            conn.commit()
            flash('員工帳號更新成功')
                
        except Exception as e:
            conn.rollback()
            flash(f'更新失敗: {e}')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('staff.staff_account.staff_list'))

    cursor.execute("SELECT * FROM role")
    roles = cursor.fetchall()
    cursor.close()
    conn.close()
        
    return render_template('staff/staff_edit.html', staff=staff, roles=roles)
