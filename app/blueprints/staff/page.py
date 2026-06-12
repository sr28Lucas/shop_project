from flask import Blueprint, session, request, redirect, render_template, url_for, flash 
from app.db import get_db_connection
from datetime import datetime
from .permission import require_permission
from app.utils.validators import Validator

page_bp = Blueprint('page', __name__) #建立藍圖

@page_bp.route('/announcement')
@require_permission('announcement')
def announcement_list():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM announcement ORDER BY pin DESC, created_at DESC")
    announcements = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('staff/announcement_list.html', announcements=announcements)

@page_bp.route('/announcement/add', methods=['GET', 'POST'])
@require_permission('announcement')
def announcement_add():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        type = request.form.get('type')
        pin = 1 if request.form.get('pin') else 0
        is_active = 1 if request.form.get('is_active') else 0
        start_at = request.form.get('start_at') or None
        end_at = request.form.get('end_at') or None
        
        if not Validator.is_valid_length(title, 100, 1):
            flash("公告標題長度需在 1-100 字元之間")
            return redirect(url_for('staff.page.announcement_list'))
        
        if not Validator.is_valid_length(content, 2000):
            flash("公告內容長度不能超過 2000 字元")
            return redirect(url_for('staff.page.announcement_list'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO announcement (title, content, type, pin, is_active, start_at, end_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, (title, content, type, pin, is_active, start_at, end_at))
        conn.commit()
        cursor.close()
        conn.close()
        flash("公告已新增")
        return redirect(url_for('staff.page.announcement_list'))
    
    return render_template('staff/announcement_add.html')

@page_bp.route('/announcement/edit/<int:id>', methods=['GET', 'POST'])
@require_permission('announcement')
def announcement_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        type = request.form.get('type')
        pin = 1 if request.form.get('pin') else 0
        is_active = 1 if request.form.get('is_active') else 0
        start_at = request.form.get('start_at') or None
        end_at = request.form.get('end_at') or None
        
        if not Validator.is_valid_length(title, 100, 1):
            flash("公告標題長度需在 1-100 字元之間")
            return redirect(url_for('staff.page.announcement_list'))
        
        if not Validator.is_valid_length(content, 2000):
            flash("公告內容長度不能超過 2000 字元")
            return redirect(url_for('staff.page.announcement_list'))
        
        cursor.execute("""
            UPDATE announcement 
            SET title=%s, content=%s, type=%s, pin=%s, is_active=%s, start_at=%s, end_at=%s, updated_at=NOW()
            WHERE id=%s
        """, (title, content, type, pin, is_active, start_at, end_at, id))
        conn.commit()
        cursor.close()
        conn.close()
        flash("公告已更新")
        return redirect(url_for('staff.page.announcement_list'))
    
    cursor.execute("SELECT * FROM announcement WHERE id = %s", (id,))
    announcement = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('staff/announcement_edit.html', announcement=announcement)

@page_bp.route('/announcement/delete/<int:id>', methods=['POST'])
@require_permission('announcement')
def announcement_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM announcement WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("公告已刪除")
    return redirect(url_for('staff.page.announcement_list'))


