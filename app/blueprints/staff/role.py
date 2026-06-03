from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.db import get_db_connection
from datetime import datetime
from .permission import require_permission

role_bp = Blueprint('role', __name__)

@role_bp.route('/list')
@require_permission('staff')
def role_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM role ORDER BY id DESC")
    roles = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('staff/role_list.html', roles=roles)

@role_bp.route('/add', methods=['GET', 'POST'])
@require_permission('staff')
def role_add():
    if request.method == 'POST':
        name = request.form.get('name')
        permissions = {
            'member': 1 if 'member' in request.form else 0,
            'orders': 1 if 'orders' in request.form else 0,
            'product': 1 if 'product' in request.form else 0,
            'inquiry': 1 if 'inquiry' in request.form else 0,
            'statistic': 1 if 'statistic' in request.form else 0,
            'staff': 1 if 'staff' in request.form else 0,
            'announcement': 1 if 'announcement' in request.form else 0,
            'return': 1 if 'return' in request.form else 0,
            'promo': 1 if 'promo' in request.form else 0,
        }
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO role (name, member, orders, product, inquiry, statistic, staff, announcement, `return`, promo, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (name, permissions['member'], permissions['orders'], permissions['product'], permissions['inquiry'], 
                  permissions['statistic'], permissions['staff'], permissions['announcement'], permissions['return'], 
                  permissions['promo'], datetime.now(), datetime.now()))
            conn.commit()
            flash('角色新增成功')
        except Exception as e:
            conn.rollback()
            flash(f'新增失敗: {e}')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('staff.role.role_list'))
        
    return render_template('staff/role_edit.html', role=None)

@role_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@require_permission('staff')
def role_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form.get('name')
        permissions = {
            'member': 1 if 'member' in request.form else 0,
            'orders': 1 if 'orders' in request.form else 0,
            'product': 1 if 'product' in request.form else 0,
            'inquiry': 1 if 'inquiry' in request.form else 0,
            'statistic': 1 if 'statistic' in request.form else 0,
            'staff': 1 if 'staff' in request.form else 0,
            'announcement': 1 if 'announcement' in request.form else 0,
            'return': 1 if 'return' in request.form else 0,
            'promo': 1 if 'promo' in request.form else 0,
        }
        
        try:
            cursor.execute("""
                UPDATE role 
                SET name=%s, member=%s, orders=%s, product=%s, inquiry=%s, statistic=%s, staff=%s, announcement=%s, `return`=%s, promo=%s, updated_at=%s
                WHERE id=%s
            """, (name, permissions['member'], permissions['orders'], permissions['product'], permissions['inquiry'], 
                  permissions['statistic'], permissions['staff'], permissions['announcement'], permissions['return'], 
                  permissions['promo'], datetime.now(), id))
            conn.commit()
            flash('角色更新成功')
        except Exception as e:
            conn.rollback()
            flash(f'更新失敗: {e}')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('staff.role.role_list'))

    cursor.execute("SELECT * FROM role WHERE id = %s", (id,))
    role = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not role:
        flash('找不到角色')
        return redirect(url_for('staff.role.role_list'))
        
    return render_template('staff/role_edit.html', role=role)

@role_bp.route('/delete/<int:id>', methods=['POST'])
@require_permission('staff')
def role_delete(id):
    if id == 1:
        flash('無法刪除 root 角色')
        return redirect(url_for('staff.role.role_list'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 檢查是否有人屬於此角色
    cursor.execute("SELECT COUNT(*) as count FROM staff WHERE role_id = %s", (id,))
    count = cursor.fetchone()['count']
    
    if count > 0:
        cursor.close()
        conn.close()
        flash(f'該角色已有 {count} 位員工使用，無法刪除')
        return redirect(url_for('staff.role.role_list'))
        
    try:
        cursor.execute("DELETE FROM role WHERE id = %s", (id,))
        conn.commit()
        flash('角色刪除成功')
    except Exception as e:
        conn.rollback()
        flash(f'刪除失敗: {e}')
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('staff.role.role_list'))
