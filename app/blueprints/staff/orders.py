from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.db import get_db_connection
import json
import os
from app.config import config

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/logistics_settings', methods=['GET', 'POST'])
def logistics_settings():
    json_path = os.path.join(config.BASE_DIR, 'app', 'static', 'json', 'taiwan_districts.json')
    
    if request.method == 'POST':
        # 處理表單提交，更新運費
        # 這裡為了簡化，直接將資料存回 JSON，也可以考慮同步更新資料庫的 region 表
        new_data = {}
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for city in data:
            fee = request.form.get(f'fee_{city}')
            if fee:
                data[city]['fee'] = float(fee)
                
                # 同步更新資料庫
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE region SET fee = %s WHERE name = %s", (float(fee), city))
                conn.commit()
                cursor.close()
                conn.close()

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        flash('運費設定已更新')
        return redirect(url_for('staff.orders.logistics_settings'))

    # GET 請求：讀取資料並顯示
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    return render_template('staff/logistics_settings.html', data=data)
