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
cursor.execute("SELECT id FROM admin WHERE email = %s", (email,))
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

    #建立權限
    permissions = [
        ('會員', 'member'),
        ('訂單', 'orders'),
        ('商品', 'product'),
        ('詢問', 'inquiry'),
        ('權限', 'permission')
    ]
    sql_perm = "INSERT IGNORE INTO permission (name,code) VALUES (%s,%s)"
    cursor.executemany(sql_perm, permissions)

    #建立角色
    sql_role = "INSERT IGNORE INTO role (name) VALUES (%s)"
    cursor.execute(sql_role, (rolename,))
    
    #賦予角色權限
    sql_rp = """
            INSERT IGNORE INTO role_permission (role_id, permission_id)
            SELECT r.id, p.id
            FROM role AS r CROSS JOIN permission AS p
            WHERE r.name = %s
            """
    cursor.execute(sql_rp, (rolename,))

    #建立root用戶
    cursor.execute("SELECT id FROM role WHERE name = %s", (rolename,))
    role_id = cursor.fetchone()['id']     
    sql_admin = """
                INSERT INTO admin (email, password, name, role_id, created_at, updated_at) 
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

