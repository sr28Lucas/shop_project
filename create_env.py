
env_content = """
#flask
DEBUG=True
SECRET_KEY=secret_key   #flask加密模組金鑰

#db參數
DATABASE_HOST = 127.0.0.1
DATABASE_USER = root
DATABASE_PASSWORD = 
DATABASE_USE = shop_project
DATABASE_CHARSET = 	utf8mb4


"""

# 将内容写入 .env 文件
with open(".env", "w") as f:
    f.write(env_content.strip())

print(".env 文件已成功生成")