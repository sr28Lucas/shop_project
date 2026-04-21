from app import create_app

# 初始化
app = create_app()

# 啟動
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

