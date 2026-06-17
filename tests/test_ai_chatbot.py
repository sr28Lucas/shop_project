import pytest
from unittest.mock import patch, MagicMock
from app.blueprints.home import chat

def test_chat_endpoint_success(client):
    """測試 AI 導購 API 成功回應"""
    # 模擬 GeminiService 回應
    with patch('app.blueprints.home.gemini_service.get_recommendation', return_value='這是一件很棒的**商品**，您可以查看 [這款商品](/product/1)。'):
        response = client.post('/api/chat', json={'query': '我想找一件外套'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'response' in data
        assert '**商品**' in data['response'] # 確保 markdown 格式保留

def test_chat_endpoint_no_query(client):
    """測試 AI 導購 API 未輸入查詢"""
    response = client.post('/api/chat', json={})
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_chat_service_logic():
    """測試 GeminiService 邏輯（Mock API）"""
    with patch('google.generativeai.GenerativeModel.generate_content') as mock_generate:
        mock_response = MagicMock()
        mock_response.text = "推薦商品A"
        mock_generate.return_value = mock_response
        
        from app.services.gemini_service import GeminiService
        service = GeminiService()
        
        result = service.get_recommendation("我想找外套", "商品A: 外套")
        
        assert result == "推薦商品A"
        assert mock_generate.called
