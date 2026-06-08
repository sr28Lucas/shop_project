import os
import shutil
import mysql.connector
import json
import sys
from datetime import datetime

"""
匯入腳本 Metadata 模式說明：
在商品資料夾下放置 metadata.json，格式如下：
{
  "abbreviation": "TWJ",      # 品名簡寫 (用於 SKU Code)
  "variants": [
    {
      "color": "米色",         # 顯示用中文名稱
      "color_code": "BE",     # SKU Code 用的顏色簡寫 (英文)
      "image_file": "123.jpg", # 對應 sku圖片/ 下的檔名
      "skus": [
        {"size": "S", "price": 990, "cost": 400, "stock": 50},
        {"size": "M", "price": 990, "cost": 400, "stock": 50}
      ]
    }
  ]
}
"""

# 確保可以匯入 app 模組
sys.path.append(os.getcwd())
from app.config import config

# 設定商品資料夾路徑
PRODUCTS_FOLDER = './商品資料'
UPLOAD_FOLDER = str(config.UPLOAD_FOLDER)

def get_db_conn():
    try:
        conn = mysql.connector.connect(**config.DB_CONFIG)
        return conn
    except Exception as e:
        print(f"資料庫連線失敗: {e}")
        return None

def save_image(cursor, source_path, product_id, variant_id=None, image_type='product', sort_order=0):
    """
    依照 staff.product 邏輯儲存圖片：
    1. 在資料庫建立記錄取得 ID
    2. 根據 ID 重新命名檔案並移動到 upload/
    3. 更新資料庫中的檔名
    """
    now = datetime.now()
    ext = os.path.splitext(source_path)[1].lower()
    
    # 1. 插入初始記錄
    sql = """
        INSERT INTO image (product_id, variant_id, image_type, filename, sort_order, created_at, updated_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (product_id, variant_id, image_type, "", sort_order, now, now))
    image_id = cursor.lastrowid
    
    # 2. 決定新檔名
    if image_type == 'variant':
        new_filename = f"v_{variant_id}_{image_id}{ext}"
    else:
        new_filename = f"{product_id}_{image_id}{ext}"
        
    dest_path = os.path.join(UPLOAD_FOLDER, new_filename)
    
    # 3. 複製檔案
    shutil.copy2(source_path, dest_path)
    
    # 4. 更新資料庫
    cursor.execute("UPDATE image SET filename = %s WHERE id = %s", (new_filename, image_id))
    return new_filename

def import_products():
    conn = get_db_conn()
    if not conn: return
    cursor = conn.cursor()

    if not os.path.exists(PRODUCTS_FOLDER):
        print(f"錯誤：找不到商品資料夾 {PRODUCTS_FOLDER}")
        return
    
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    now = datetime.now()
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif')

    print(f"🚀 開始匯入商品 (Metadata 模式)...\n")

    for category_name in sorted(os.listdir(PRODUCTS_FOLDER)):
        category_path = os.path.join(PRODUCTS_FOLDER, category_name)
        if not os.path.isdir(category_path): continue

        print(f"🏷️  分類: {category_name}")
        
        # 取得或建立分類
        cursor.execute("SELECT id FROM category WHERE name = %s", (category_name,))
        cat = cursor.fetchone()
        if cat:
            category_id = cat[0]
        else:
            cursor.execute("INSERT INTO category (name, created_at, updated_at) VALUES (%s, %s, %s)", (category_name, now, now))
            category_id = cursor.lastrowid

        for product_name in sorted(os.listdir(category_path)):
            product_path = os.path.join(category_path, product_name)
            if not os.path.isdir(product_path): continue

            print(f"   📦 商品: {product_name}")
            
            # 讀取描述
            description = "透過批次匯入的商品"
            desc_file = os.path.join(product_path, '描述.txt')
            if os.path.exists(desc_file):
                with open(desc_file, 'r', encoding='utf-8') as f:
                    content = f.read().splitlines()
                    if len(content) >= 3:
                        description = "\n".join(content[2:]).strip()

            # 建立商品
            try:
                cursor.execute("""
                    INSERT INTO product (category_id, name, description, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, 1, %s, %s)
                """, (category_id, product_name, description, now, now))
                product_id = cursor.lastrowid

                # --- 匯入商品圖片 (主圖與輪播) ---
                img_dir = os.path.join(product_path, '商品圖片')
                if os.path.exists(img_dir):
                    images = [f for f in sorted(os.listdir(img_dir)) if f.lower().endswith(valid_extensions)]
                    for idx, img_name in enumerate(images):
                        source = os.path.join(img_dir, img_name)
                        new_name = save_image(cursor, source, product_id, image_type='product', sort_order=idx)
                        # 第一張設為主圖
                        if idx == 0:
                            cursor.execute("UPDATE image SET is_primary = 1 WHERE filename = %s", (new_name,))
                        print(f"      📷 匯入商品圖: {new_name}")

                # --- 匯入變體與 SKU (Metadata) ---
                meta_file = os.path.join(product_path, 'metadata.json')
                if os.path.exists(meta_file):
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    
                    abbrev = meta.get('abbreviation', 'PROD')
                    
                    for v_data in meta.get('variants', []):
                        color_zh = v_data.get('color')
                        color_en = v_data.get('color_code', 'UNK')
                        
                        # 建立變體 (顯示用中文)
                        cursor.execute("""
                            INSERT INTO variant (product_id, color, is_active, created_at, updated_at)
                            VALUES (%s, %s, 1, %s, %s)
                        """, (product_id, color_zh, now, now))
                        variant_id = cursor.lastrowid
                        
                        # 處理變體圖片
                        v_img_filename = v_data.get('image_file')
                        if v_img_filename:
                            # 優先找 sku圖片 資料夾
                            v_img_source = os.path.join(product_path, 'sku圖片', v_img_filename)
                            if not os.path.exists(v_img_source):
                                # 嘗試不區分大小寫的資料夾名稱
                                v_img_source = os.path.join(product_path, 'SKU圖片', v_img_filename)
                                
                            if os.path.exists(v_img_source):
                                new_v_name = save_image(cursor, v_img_source, product_id, variant_id, 'variant')
                                print(f"      🎨 匯入變體圖: {new_v_name} ({color_zh})")
                        
                        # 建立 SKU
                        for s_data in v_data.get('skus', []):
                            size = s_data.get('size', 'F')
                            # SKU Code: <品名簡寫><顏色英文><尺寸>
                            sku_code = f"{abbrev}{color_en}{size}".upper()
                            
                            cursor.execute("""
                                INSERT INTO sku (variant_id, sku_code, size, price, cost, stock, is_active, created_at, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s)
                            """, (variant_id, sku_code, size, s_data['price'], s_data['cost'], s_data['stock'], now, now))
                            print(f"         🏷️  建立 SKU: {sku_code}")
                
                conn.commit()
                print(f"   ✅ {product_name} 匯入成功\n")
            except Exception as e:
                conn.rollback()
                print(f"   ❌ {product_name} 匯入失敗: {e}\n")

    cursor.close()
    conn.close()
    print("✨ 全部匯入程序完成")

if __name__ == "__main__":
    import_products()
