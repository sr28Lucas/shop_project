# 電商網站期末專案

## 安裝
### 1.啟用.venv
```bash
python -m venv .venv
# Windows 啟用方式
.\.venv\Scripts\activate
# Linux / macOS 啟用方式
source .venv/bin/activate
```

### 2.安裝依賴項
```bash
pip install -r requirements.txt
```
學校的容器環境可能會少編譯要用的運行庫
```bash
apt update
apt install python3-dev default-libmysqlclient-dev build-essential
```

### 3.導入資料庫
將.sql導入

### 4.設定環境變數
生成.env
```bash
python create_env.py
```
修改參數

### 5.關閉Apache2
```bash
sudo service apache2 stop
```

### 6.匯入資料庫結構
```bash
mysql -u root -h 127.0.0.1 shop_db < shop_database.sql
```

### 7.執行初始化腳本
```bash
python setup.py
```

### 啟動
```bash
python run.py
```

### 自動清除資料庫
當資料庫架構有變時使用
```bash
python reset_db.py
```
輸入 'y' 確認刪除舊資料表

---

## 帳號與存取資訊
### 預設管理員帳密 (Root)
* **Email:** `root@root`
* **Password:** `root`

### 網站登入地址
* **網站首頁:** `http://[你的IPv4]/`
* **管理員登入:** `http://[你的IPv4]/auth/staff_login`
#### port撞了就自己改一下
