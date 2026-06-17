# 電商網站系統 (E-commerce Platform)

這是一個基於 **Flask** 框架開發的全功能服飾電商網站系統，具備完整的會員中心、商品展示、購物流程以及強大的後台管理系統（含 RBAC 權限控管）。

---

## 🚀 核心功能

### 🛒 前台功能 (Customer Side)
*   **商品瀏覽:** 多層次分類展示、商品詳細資訊、多規格 (SKU) 選擇、商品圖片輪播。
*   **AI 導購:** 整合 AI 提供智慧商品推薦。
*   **會員系統:** 註冊、登入（Bcrypt 加密）、忘記密碼、個人資料編輯、密碼修改。
*   **購物車 & 結帳:** 靈活的購物車管理、串接台灣地區與運費計算的結帳流程。
*   **訂單管理:** 查看訂單狀態、詳細訂單內容、申請退貨處理。
*   **追蹤清單:** 會員可收藏喜愛的商品。
*   **客戶支援:** 提交諮詢表單 (Inquiry)、查看系統公告。

### 🛡️ 後台管理 (Staff Side - Admin Dashboard)
*   **儀表板:** 系統概況與快速導航、營收與統計分析。
*   **商品管理:** 
    *   **分類管理:** 階層式商品分類。
    *   **商品維護:** 編輯商品描述、批次管理圖片、啟用/禁用商品。
    *   **規格 (SKU) 管理:** 管理顏色、尺寸、價格、成本、庫存。
    *   **潛力爆款分析:** 數據驅動的商品分析。
*   **訂單管理:** 處理訂單、修改訂單狀態、查看訂單歷史。
*   **退貨處理:** 審核與管理退貨申請。
*   **促銷管理:** 系統促銷活動設定與優惠碼系統。
*   **RBAC 權限管理:** 
    *   自定義角色 (Roles) 及其對應模組的操作權限。
    *   管理員帳號分配不同角色。
*   **客戶支援系統:** 回覆客戶諮詢 (Inquiry)、發布與編輯系統公告。
*   **數據統計:** 營收與銷量統計報表。
*   **物流設定:** 設定不同縣市的運費標準。

---

## 🛠 技術棧
*   **後端:** Python 3.x, Flask
*   **資料庫:** MySQL (搭配 `mysqlclient` 或 `mysql-connector-python`)
*   **前端:** HTML5, CSS3, JavaScript (Vanilla JS), Jinja2 模板引擎
*   **安全:** Flask-Bcrypt (密碼雜湊加密)
*   **環境:** python-dotenv (環境變數管理)
*   **測試:** Pytest (完整的功能測試套件)

---

## 📂 專案結構
```text
C:\project\shop_project\
├── app\                    # Flask 應用核心
│   ├── blueprints\         # 模組化藍圖 (auth, customer, home, staff)
│   │   ├── staff\          # 後台管理藍圖 (含多個子功能模組)
│   ├── static\             # 靜態資源 (CSS, JS, 圖片, JSON 資料)
│   ├── templates\          # HTML 模板
│   ├── config.py           # 應用配置
│   ├── db.py               # 資料庫連線管理
│   └── extensions.py       # Flask 套件擴展 (Bcrypt 等)
├── docs\                   # 相關文件 (ER Model, 圖表)
├── tests\                  # 自動化測試案例
├── 商品資料\               # 初始商品匯入資料 (含 metadata.json 與圖片)
├── create_env.py           # 生成 .env 範本腳本
├── import_item.py          # 批次匯入商品腳本
├── setup.py                # 系統初始化腳本 (建立 root 帳號與地區)
├── run.py                  # 應用啟動進入點
├── latest_資料庫系統_電商網站_20260615.sql # 資料庫架構與預設資料
```

---

## ⚙️ 安裝與快速上手

### 1. 建立虛擬環境
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
```

### 2. 安裝依賴項
```bash
pip install -r requirements.txt
```

### 3. 設定環境變數
執行以下腳本生成 `.env` 檔案：
```bash
python create_env.py
```
**請編輯 `.env` 檔案**，填入您的 MySQL 資料庫連線資訊：
```env
DATABASE_HOST = 127.0.0.1
DATABASE_USER = your_user
DATABASE_PASSWORD = your_password
DATABASE_USE = shop_db
```

### 4. 初始化資料庫
1.  **手動建立資料庫:** 在 MySQL 中建立名稱為 `shop_db` (或您在 .env 設定的名稱) 的資料庫。
2.  **匯入 SQL 架構:**
    ```bash
    mysql -u root -p shop_db < latest_資料庫系統_電商網站_20260615.sql
    ```
3.  **執行系統初始化:** (建立 root 管理員帳號與台灣運費資料)
    ```bash
    python setup.py
    ```

### 5. 匯入商品資料 (選用)
本系統提供自動化匯入工具，可將 `商品資料/` 資料夾下的商品與圖片自動同步至系統與資料庫：
```bash
python import_item.py
```

### 6. 啟動系統
```bash
python run.py
```
預設訪問地址：`http://127.0.0.1:80/`

---

## 🔐 預設帳號資訊
*   **超級管理員 (Root):**
    *   **Email:** `root@root`
    *   **Password:** `root`
*   **管理後台路徑:** `http://127.0.0.1/auth/staff_login`

---

## 🧪 測試
專案包含豐富的測試案例，位於 `tests/` 目錄。
```bash
cd tests
python -m pytest  # 或是執行 ./test.ps1 (Windows)
```

## 📜 授權說明
本專案為期末專案，僅供教學與研究使用。
