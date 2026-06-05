import pytest
from app.db import get_db_connection
from datetime import datetime

@pytest.fixture
def test_inquiry(client):
    """建立一個測試用的客服案件"""
    # 建立客戶
    email = f'cust_{datetime.now().timestamp()}@test.com'
    client.post('/auth/register', data={'email': email, 'password': 'password', 'confirm_password': 'password', 'name': 'Inquiry User'})
    client.post('/auth/login', data={'email': email, 'password': 'password'})
    
    # 提交案件
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM customer WHERE email = %s", (email,))
    cust_id = cursor.fetchone()[0]
    
    cursor.execute("INSERT INTO inquiry (customer_id, purpose, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s)",
                   (cust_id, '測試問題', 'open', datetime.now(), datetime.now()))
    inq_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return inq_id

def test_inquiry_flow(client, auth_staff, test_inquiry):
    """測試客服後台流程"""
    # 1. 列表頁
    response = client.get('/staff/inquiry/active')
    assert response.status_code == 200
    assert "測試問題" in response.get_data(as_text=True)
    
    # 2. 詳情頁
    response = client.get(f'/staff/inquiry/detail/{test_inquiry}')
    assert response.status_code == 200
    
    # 3. 回覆案件
    response = client.post(f'/staff/inquiry/reply/{test_inquiry}', data={'content': '客服回覆測試'})
    assert response.status_code == 302 # 重導向
    
    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT content FROM message WHERE inquiry_id = %s", (test_inquiry,))
    msg = cursor.fetchone()
    assert msg['content'] == '客服回覆測試'
    cursor.close()
    conn.close()
