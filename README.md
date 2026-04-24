# 電商網站期末專案

## 安裝
### 1.啟用.venv
```bash
python -m venv .venv
# Windows 啟用方式
.\venv\Scripts\activate
# Linux / macOS 啟用方式
source .venv/bin/activate
```

### 2.安裝依賴項
```bash
pip install -r requirements.txt
```

### 3.導入資料庫
將.sql導入

### 4.設定環境變數
生成.env
```bash
python create_env.py
```
修改參數

### 5.執行初始化腳本
```bash
python setup.py
```

### 啟動
```bash
python run.py
```

---

## 帳號與存取資訊
### 預設管理員帳密 (Root)
* **Email:** `root@root`
* **Password:** `root`

### 網站登入地址
* **一般會員登入:** `[你的IPv4]:[Port(8080)]/auth/login`
* **管理員登入:** `[你的IPv4]:[Port(8080)]/auth/admin-login`
