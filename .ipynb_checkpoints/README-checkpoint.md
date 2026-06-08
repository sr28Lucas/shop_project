# 電商網站期末專案

這是一個基於 Flask 框架開發的服飾網站系統。

## 技術棧
* **後端:** Python, Flask
* **資料庫:** MySQL
* **前端:** HTML, CSS, JavaScript
* **密碼加密:** Flask-Bcrypt

---

## 環境需求
* Python 3.x
* MySQL Server
* `pip` 相關依賴 (詳見 `requirements.txt`)

---

## 安裝指南

### 1. 建立並啟用虛擬環境
```bash
# 建立虛擬環境
python -m venv .venv

# 啟用虛擬環境 (Windows)
.\.venv\Scripts\activate

# 啟用虛擬環境 (Linux / macOS)
source .venv/bin/activate
```

### 2. 安裝依賴項
```bash
pip install -r requirements.txt
```
*(注意：如在 Linux 環境部署，可能需要額外安裝系統依賴，例如 `python3-dev`, `default-libmysqlclient-dev`, `build-essential`)*

### 3. 設定環境變數
請建立 `.env` 檔案以存放敏感配置資訊。您可以使用提供的腳本生成範本：
```bash
python create_env.py
```
隨後請務必修改 `.env` 檔案中的資料庫連線參數與金鑰。

### 4. 資料庫設定與初始化
1. **建立資料庫:** 在 MySQL 中建立對應的資料庫（名稱需與 `.env` 中設定的一致）。
2. **匯入架構:** 使用最新的 SQL 檔案匯入資料庫結構：
   ```bash
   mysql -u [使用者名稱] -p [資料庫名稱] < latest_資料庫系統_電商網站_20260603.sql
   ```
3. **執行系統初始化:** 初始化腳本會建立預設管理員帳號與匯入台灣地區資訊：
   ```bash
   python setup.py
   ```
### 5. 匯入商品
   ```bash
   python import_item.py
   ```
---

## 啟動系統
使用以下指令啟動 Flask 開發伺服器：
```bash
python run.py
```
預設網站運行在 `http://127.0.0.1:8080/` (請根據 `run.py` 設定調整)。

---

## 帳號與管理

### 預設管理員帳號
* **Email:** `root@root`
* **Password:** `root`

### 系統管理路徑
* **網站首頁:** `http://[IPv4]/`
* **管理員登入:** `http://[IPv4]/auth/staff_login`

---
