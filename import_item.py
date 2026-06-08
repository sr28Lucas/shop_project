import os
import shutil
import mysql.connector
from datetime import datetime

# 設定商品資料夾路徑
PRODUCTS_FOLDER = '/home/jovyan/workspace/shop_project/商品資料'
UPLOAD_FOLDER = '/home/jovyan/workspace/shop_project/app/static/upload'

def import_products_and_images():
    # 1. 建立資料庫連線
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='',
            database='shop_db'
        )
        cursor = conn.cursor()
    except Exception as e:
        print(f"資料庫連線失敗: {e}")
        return

    # 2. 檢查資料夾是否存在
    if not os.path.exists(PRODUCTS_FOLDER):
        print(f"錯誤：找不到商品資料夾 {PRODUCTS_FOLDER}")
        return
    
    # 確保上傳資料夾存在
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        print(f"✓ 建立上傳資料夾: {UPLOAD_FOLDER}\n")

    # 3. 準備 SQL 插入語法
    sql_insert_category = """
        INSERT INTO category (name, created_at, updated_at) 
        VALUES (%s, %s, %s)
    """

    sql_insert_product = """
        INSERT INTO product (category_id, name, description, is_active, created_at, updated_at) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    sql_insert_image = """
        INSERT INTO image (product_id, filename, image_type, is_primary, created_at, updated_at) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    sql_select_category = "SELECT id FROM category WHERE name = %s"

    success_count = 0
    error_count = 0
    now = datetime.now()
    valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif')

    print(f"開始匯入商品...\n")

    # 遍歷分類資料夾
    for category_name in sorted(os.listdir(PRODUCTS_FOLDER)):
        category_path = os.path.join(PRODUCTS_FOLDER, category_name)
        
        if not os.path.isdir(category_path):
            continue

        print(f"🏷️  分類: {category_name}")

        # 確認或新增分類
        try:
            cursor.execute(sql_select_category, (category_name,))
            cat = cursor.fetchone()
            if cat:
                category_id = cat[0]
                print(f"   ✓ 使用現有分類 ID: {category_id}")
            else:
                cursor.execute(sql_insert_category, (category_name, now, now))
                category_id = cursor.lastrowid
                conn.commit()
                print(f"   ✓ 新增分類 ID: {category_id}")
        except mysql.connector.Error as e:
            conn.rollback()
            print(f"   ❌ 分類錯誤: {e}")
            error_count += 1
            continue

        # 在 upload 資料夾中建立分類子資料夾
        category_upload_path = os.path.join(UPLOAD_FOLDER, category_name)
        if not os.path.exists(category_upload_path):
            os.makedirs(category_upload_path)

        # 遍歷商品資料夾
        for product_name in sorted(os.listdir(category_path)):
            product_path = os.path.join(category_path, product_name)
            
            if not os.path.isdir(product_path):
                continue

            print(f"   📦 商品: {product_name}")

            # 讀取描述檔案
            description_file = os.path.join(product_path, '描述.txt')
            description = "透過 Python 腳本批次匯入的商品"
            if os.path.exists(description_file):
                try:
                    with open(description_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if len(lines) > 2:
                            description = ''.join(lines[2:]).strip()
                except Exception as e:
                    print(f"      ⚠️  讀取描述檔失敗: {e}")

            # 新增商品
            try:
                val_product = (category_id, product_name, description, 1, now, now)
                cursor.execute(sql_insert_product, val_product)
                product_id = cursor.lastrowid
                conn.commit()
                print(f"      ✓ 商品 ID: {product_id}")
            except mysql.connector.Error as e:
                conn.rollback()
                print(f"      ❌ 新增商品失敗: {e}")
                error_count += 1
                continue

            # 在 upload 資料夾中建立商品子資料夾
            product_upload_path = os.path.join(category_upload_path, product_name)
            if not os.path.exists(product_upload_path):
                os.makedirs(product_upload_path)

            # 匯入商品圖片 (複製到 upload 資料夾並保持分類結構)
            product_images_path = os.path.join(product_path, '商品圖片')
            if os.path.exists(product_images_path):
                image_files = [f for f in sorted(os.listdir(product_images_path)) 
                              if f.lower().endswith(valid_extensions)]
                
                for idx, image_file in enumerate(image_files):
                    try:
                        # 複製圖片到 upload/分類/商品/ 資料夾
                        source_path = os.path.join(product_images_path, image_file)
                        dest_path = os.path.join(product_upload_path, image_file)
                        
                        shutil.copy2(source_path, dest_path)
                        
                        # 儲存相對路徑 (從 upload 資料夾開始)
                        # 例如: 男短袖上衣/貼身Polo衫/image.avif
                        relative_path = os.path.join(category_name, product_name, image_file)
                        
                        # 新增圖片記錄到資料庫
                        is_primary = 1 if idx == 0 else 0
                        val_image = (product_id, relative_path, 'product', is_primary, now, now)
                        cursor.execute(sql_insert_image, val_image)
                        conn.commit()
                        success_count += 1
                        print(f"        📷 {relative_path}" + (" (主圖)" if is_primary else ""))
                    except mysql.connector.Error as e:
                        conn.rollback()
                        print(f"        ❌ 圖片 {image_file}: {e}")
                        error_count += 1
                    except Exception as e:
                        print(f"        ❌ 複製圖片失敗 {image_file}: {e}")
                        error_count += 1
            else:
                print(f"      ⚠️  找不到商品圖片資料夾")

    # 4. 關閉連線
    cursor.close()
    conn.close()

    print(f"\n{'='*60}")
    print(f"✅ 執行完畢！")
    print(f"   📦 成功建立: {success_count} 個商品與圖片")
    print(f"   ❌ 失敗: {error_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    import_products_and_images()
