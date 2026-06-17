import os
import google.generativeai as genai
from app.config import config

class GeminiService:
    def __init__(self):
        self.api_key = config.AI_CONFIG['gemini_api_key']
        self.model_name = config.AI_CONFIG['gemini_model']
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in the configuration.")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def get_recommendation(self, user_query, product_context):
        prompt = f"""
        你是電商網站的專業導購助手。請根據以下商品資料，針對顧客的需求提供精確的產品推薦。
        如果資料中沒有符合的商品，請誠實告知，不要隨意推薦。
        
        顧客提問: {user_query}
        
        可用商品資料:
        {product_context}
        
        請以友善、簡潔的口吻回覆。
        對於推薦的商品，請務必使用 Markdown 連結格式 [商品名稱](/product/商品ID) 來提供連結。
        """
        
        response = self.model.generate_content(prompt)
        return response.text
