from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.db import get_db_connection
from app.extensions import bcrypt

staff_profile_bp = Blueprint('staff_profile', __name__)

def get_staff_data(staff_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM staff WHERE id = %s", (staff_id,))
        staff = cursor.fetchone()
        role = None
        if staff:
            cursor.execute("SELECT * FROM role WHERE id = %s", (staff['role_id'],))
            role = cursor.fetchone()
        return staff, role
    finally:
        cursor.close()
        conn.close()

@staff_profile_bp.route('/', methods=['GET', 'POST'])
def edit_profile():
    print(f"DEBUG: Entering edit_profile. Session: {session}")
    staff_id = session.get('staff_id')
    print(f"DEBUG: staff_id in edit_profile: {staff_id}")
    if not staff_id:
        print("DEBUG: No staff_id, redirecting to login")
        return redirect(url_for('auth.staff_login'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        if not name:
            flash("姓名為必填", "error")
            return redirect(url_for('staff.staff_profile.edit_profile'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE staff 
                SET name = %s, phone = %s, updated_at = NOW() 
                WHERE id = %s
            """, (name, phone or None, staff_id))
            conn.commit()
            flash("個人資料更新成功！", "success")
        except Exception as e:
            conn.rollback()
            flash(f"更新失敗: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('staff.staff_profile.edit_profile'))
            
    staff, role = get_staff_data(staff_id)
    return render_template('staff/profile_edit.html', user=staff, role=role, staff=staff)

@staff_profile_bp.route('/test-link')
def test_link():
    return "Profile routes are accessible!"

@staff_profile_bp.route('/password', methods=['GET', 'POST'])
def change_password():
    print(f"DEBUG: Entering change_password. Session: {session}")
    staff_id = session.get('staff_id')
    print(f"DEBUG: staff_id in change_password: {staff_id}")
    if not staff_id:
        print("DEBUG: No staff_id, redirecting to login")
        return redirect(url_for('auth.staff_login'))
        
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            flash("請填寫所有欄位", "error")
            return redirect(url_for('staff.staff_profile.change_password'))
        
        if new_password != confirm_password:
            flash("新密碼與確認密碼不一致", "error")
            return redirect(url_for('staff.staff_profile.change_password'))
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT password FROM staff WHERE id = %s", (staff_id,))
            staff = cursor.fetchone()
            
            if staff and bcrypt.check_password_hash(staff['password'], old_password):
                hashed_pw = bcrypt.generate_password_hash(new_password).decode('utf-8')
                cursor.execute("UPDATE staff SET password = %s, updated_at = NOW() WHERE id = %s", 
                               (hashed_pw, staff_id))
                conn.commit()
                flash("密碼修改成功！", "success")
            else:
                flash("原密碼錯誤", "error")
        except Exception as e:
            conn.rollback()
            flash(f"修改密碼失敗: {str(e)}", "error")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('staff.staff_profile.change_password'))
            
    staff, role = get_staff_data(staff_id)
    return render_template('staff/password_edit.html', user=staff, role=role)

