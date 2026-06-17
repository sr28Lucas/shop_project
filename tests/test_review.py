import pytest
from app.db import get_db_connection

def test_add_review_terminology_and_functionality(client, test_order, test_product):
    """測試評價功能中 '品質' 術語的顯示與功能正常"""
    
    # 1. 登入 (需先找到對應訂單的使用者，或者在 conftest 中已登入)
    # 根據 conftest，test_order fixture 會自動執行購買流程，且登入了對應的 buyer
    # 我們需要重新登入或確保 session 是正確的。
    # 簡單的做法是重新登入
    email = f'buyer_{test_order["order_id"]}@test.com' # 模擬上面的 buyer 郵件結構
    # 實際上 conftest 中 buyer 郵件是動態的，我們需直接使用已註冊過的使用者
    # 上面的 test_order 沒回傳 user，沒關係，我們先登入
    
    # 重新登入 (為了測試)
    # (簡單起見，直接請求訂單頁面，若未登入會被導向登入頁，這裡先假定需要登入)
    # ...
    
    # 由於 `test_order` 會自動下單並登入，這裡直接嘗試獲取頁面
    print(f"URL: /customer/order/view/{test_order['order_id']}")
    response = client.get(f'/customer/order/view/{test_order["order_id"]}')
    print(f"Status: {response.status_code}")
    assert response.status_code == 200

    # 驗證 UI 是否已改為 "品質"
    data = response.get_data(as_text=True)
    assert "品質" in data
    assert "質量" not in data
    
    # 2. 提交評價
    from flask import url_for
    with client.application.app_context():
        url = url_for('home.add_review')
        print(f"Review URL: {url}")
    
    response = client.post(url, data={
        'product_id': test_product['product_id'],
        'order_item_id': test_order['item_id'],
        'overall_rating': '5',
        'quality_rating': '4',
        'comfort_rating': '5',
        'value_rating': '5',
        'fit_feedback': '0',
        'comment': '品質很好，推薦！'
    }, follow_redirects=True, headers={'Referer': f'/customer/order/view/{test_order["order_id"]}'})
    print(f"Review Post Status: {response.status_code}")
    
    assert response.status_code == 200
    
    # 3. 驗證商品詳情頁是否顯示 "品質"
    response = client.get(f'/product/{test_product["product_id"]}')
    assert response.status_code == 200
    
    data = response.get_data(as_text=True)
    assert "品質" in data
    assert "質量" not in data
    # 驗證分數 (應該有顯示 4.0)
    assert "4.0" in data or "4.00" in data
