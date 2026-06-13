
env_content = """
#flask
DEBUG=True
SECRET_KEY=secret_key   # Flask Secret Key

#db
DATABASE_HOST = 127.0.0.1
DATABASE_USER = root
DATABASE_PASSWORD = 
DATABASE_USE = shop_db
DATABASE_CHARSET = 	utf8mb4


"""

# 寫入.env 
with open(".env", "w") as f:
    f.write(env_content.strip())

print(".env 文件已成功生成")