from app.db import get_db_connection
import sys

def clear_database():
    print("準備清空資料庫...")
    conn = get_db_connection()
    # 這裡不特別指定 dictionary=True，以兼容不同套件的預設值
    cursor = conn.cursor() 

    try:
        # 1. 關閉外鍵檢查 (超級重要！這樣才能無視關聯，強制刪除資料表)
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # 2. 抓出目前資料庫裡所有的資料表
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()

        if not tables:
            print("✅ 資料庫已經是空的，不需要清理！")
        else:
            for table in tables:
                # 兼容 tuple 或 dict 的回傳格式
                table_name = list(table.values())[0] if isinstance(table, dict) else table[0]
                
                # 刪除資料表
                cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
                print(f"🗑️  已刪除資料表: {table_name}")

        # 3. 重新開啟外鍵檢查，恢復正常狀態
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()
        print("✨ 資料庫清空完成！現在你可以重新執行 setup.py 了。")

    except Exception as e:
        print(f"❌ 清空資料庫時發生錯誤: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # 防呆機制，避免你不小心按到把辛苦建的資料刪光
    print("⚠️  警告：此操作將會刪除資料庫中的【所有資料表與資料】！")
    confirm = input("確定要繼續嗎？(輸入 y 繼續 / 任意鍵取消): ")
    
    if confirm.lower() == 'y':
        clear_database()
    else:
        print("🛑 已取消操作。")