import pytest
from app.db import get_db_connection

def test_statistic_revenue_access(client, auth_staff):
    """測試營收統計頁面存取"""
    response = client.get('/staff/statistic/revenue')
    assert response.status_code == 200
    assert "營收" in response.get_data(as_text=True)

def test_statistic_sales_access(client, auth_staff):
    """測試銷售統計頁面存取"""
    response = client.get('/staff/statistic/sales')
    assert response.status_code == 200
    assert "銷售" in response.get_data(as_text=True)
