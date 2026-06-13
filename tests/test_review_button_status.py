import pytest
from app.db import get_db_connection

def test_review_button_status_ui(client, test_order, test_product):
    """驗證評論按鈕在已評論後變更為 '已完成評論'"""
    
    # 1. 確保訂單已完成
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'completed' WHERE id = %s", (test_order['order_id'],))
    conn.commit()
    cursor.close()
    conn.close()

    # 2. 獲取訂單頁面 (未評論狀態)
    response = client.get(f'/customer/order/view/{test_order["order_id"]}')
    assert response.status_code == 200
    data = response.get_data(as_text=True)
    assert "撰寫評價" in data
    assert "已完成評論" not in data

    # 3. 提交評價
    from flask import url_for
    with client.application.app_context():
        url = url_for('home.add_review')
    
    client.post(url, data={
        'product_id': test_product['product_id'],
        'order_item_id': test_order['item_id'],
        'overall_rating': '5',
        'quality_rating': '4',
        'comfort_rating': '5',
        'value_rating': '5',
        'fit_feedback': '0',
        'comment': '測試評論'
    }, follow_redirects=True, headers={'Referer': f'/customer/order/view/{test_order["order_id"]}'})

    # 4. 再次獲取訂單頁面 (已評論狀態)
    response = client.get(f'/customer/order/view/{test_order["order_id"]}')
    assert response.status_code == 200
    data = response.get_data(as_text=True)
    
    # 驗證按鈕已變更
    assert "已完成評論" in data
    assert "撰寫評價" not in data
    assert "disabled" in data # 檢查按鈕是否為 disabled
