# 前端測試覆蓋追蹤矩陣 (Frontend Coverage Matrix)

此矩陣用於追蹤各個 HTML 模板與前端功能模組的測試覆蓋狀態。
目標：確保所有模板皆被驗證 (至少達到頁面可正確渲染的基礎整合測試)。

## 狀態說明
- [ ] 未測試
- [~] 基礎測試 (確認 HTTP 200/302 與關鍵元件存在)
- [x] 完整測試 (包含邏輯驗證、表單提交、負面測試)

### 客戶端 (Front-end)
| 模組 | 模板檔案 | 測試狀態 | 備註 |
| :--- | :--- | :--- | :--- |
| **Auth** | `auth/login.html` | [x] | 整合 Auth 負面測試 |
| **Auth** | `auth/register.html` | [x] | 整合 Auth 負面測試 |
| **Home** | `home/base.html` | [~] | 透過首頁測試覆蓋 |
| **Home** | `home/index.html` | [x] | 完整渲染與導航測試 |
| **Home** | `home/cart.html` | [x] | 購物車狀態與互動邏輯 |
| **Home** | `home/information.html` | [~] | 基礎渲染測試 |
| **Home** | `home/wishlist.html` | [~] | 基礎渲染測試 |
| **Customer**| `customer/profile_edit.html` | [x] | 包含資料/密碼驗證測試 |
| **Customer**| `customer/order_list.html` | [x] | 包含訂單檢視測試 |

### 管理端 (Back-end)
| 模組 | 模板檔案 | 測試狀態 | 備註 |
| :--- | :--- | :--- | :--- |
| **Staff** | `staff/dashboard.html` | [~] | 基礎渲染測試 |
| **Staff** | `staff/product_list.html` | [x] | CRUD 與批次狀態更新 |
| **Staff** | `staff/product_add.html` | [x] | 商品新增邏輯驗證 |
| **Staff** | `staff/order_list.html` | [~] | 基礎渲染與權限測試 |
| **Staff** | `staff/member_list.html` | [x] | 包含 CRUD 與狀態切換測試 |
| **Staff** | `staff/profile_edit.html` | [x] | 管理員資料編輯驗證 |
| **Staff** | `staff/statistic_revenue.html`| [x] | 營收統計與退貨扣除驗證 |

*註：`app/static/upload` 中的圖片檔案無需進行功能測試。*
