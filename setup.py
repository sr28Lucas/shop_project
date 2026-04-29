from app.db import get_db_connection
from flask_bcrypt import Bcrypt
from datetime import datetime
import sys
from app.config import config



email = 'root@root'
password = 'root'
name = 'root'
rolename = 'root'


print(config.DB_CONFIG)
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

# 檢查 Email 是否存在
cursor.execute("SELECT id FROM staff WHERE email = %s", (email,))
if cursor.fetchone():
    print('admin: root 已存在 程式中止')
    cursor.close()
    conn.close()
    sys.exit('帳戶已存在')
# 密碼加密
bcrypt = Bcrypt()
hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


try:
    #建立root角色
    sql_role = """
            INSERT INTO role (name, member, orders, product, inquiry, statistic, staff, created_at, updated_at)
            VALUES (%s, 1, 1, 1, 1, 1, 1, %s, %s)            
            """
    cursor.execute(sql_role, (rolename, now, now))


    #建立root用戶
    cursor.execute("SELECT id FROM role WHERE name = %s", (rolename,))
    role_id = cursor.fetchone()['id']     
    sql_admin = """
                INSERT INTO staff (email, password, name, role_id, created_at, updated_at) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
    cursor.execute(sql_admin, (email, hashed_pw, name, role_id, now, now))
    
    conn.commit()
    print("系統初始化成功")

except Exception as e:
    conn.rollback()
    print(f"初始化失敗:{e}")
    sys.exit(1)
finally:
    cursor.close()
    conn.close()

