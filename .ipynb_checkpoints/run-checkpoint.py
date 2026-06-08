import sys
from app import create_app
from app.db import get_db_connection

# 檢查資料庫是否已初始化 (確認 root 帳號是否存在)
def check_db_initialized():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 檢查是否存在 root 帳號
        cursor.execute("SELECT id FROM staff WHERE email = 'root@root'")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result is not None
    except Exception as e:
        return False

if not check_db_initialized():
    print("資料庫連線失敗或尚未初始化，請確認 .env 設定並執行 'python setup.py' 進行安裝。")
    sys.exit(1)

# 初始化
app = create_app()

# 啟動
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

