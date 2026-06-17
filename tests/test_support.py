import pytest
from flask import session
from unittest.mock import patch
from app.db import get_db_connection

def test_support_new_inquiry_redirect(client):
    """未登入應重定向至登入頁"""
    # 測試腳本在測試重定向時，應檢查實際的重定向位置，而非假設應用程式邏輯
    response = client.get('/support/new', follow_redirects=False)
    assert response.status_code == 302
    assert "login" in response.location

def test_support_new_inquiry_success(client, auth_client):
    """測試成功建立客服案件"""
    with patch('app.blueprints.home.support.require_customer_login', return_value=True):
        with client.session_transaction() as sess:
            sess['customer_id'] = 1
        
        response = client.post('/support/new', data={
            'purpose': 'Test Subject',
            'content': 'Test Content'
        }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # 驗證資料庫
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM inquiry WHERE purpose = 'Test Subject' AND customer_id = 1")
    inquiry = cursor.fetchone()
    assert inquiry is not None
    cursor.close()
    conn.close()

def test_support_list_inquiries(client, auth_client):
    """測試客服案件列表"""
    with patch('app.blueprints.home.support.require_customer_login', return_value=True):
        with client.session_transaction() as sess:
            sess['customer_id'] = 1
        
        response = client.get('/support/list', follow_redirects=True)
    assert response.status_code == 200

def test_support_refund_redirect(client):
    """測試退貨申請重定向至訂單列表"""
    response = client.get('/support/refund', follow_redirects=True)
    assert response.status_code == 200
    assert "退貨申請系統已更新" in response.get_data(as_text=True)
