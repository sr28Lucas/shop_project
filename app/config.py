import os
from dotenv import load_dotenv
from pathlib import Path


# 載入 .env 檔案中的變數
dotenv_path = Path(__file__).resolve().parent / '..' / '.env'
load_dotenv(dotenv_path = dotenv_path) 


class config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret_key' #加密金鑰 要這才可以用flask的加密功能
    SQLALCHEMY_TRACK_MODIFICATIONS = False #某個看不懂但應該用不到的功能 開了似乎會吃效能
 
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False

    UPLOAD_FOLDER = Path(__file__).resolve().parent / 'static' / 'upload'
    
    print(UPLOAD_FOLDER)

    DB_CONFIG = { #資料庫參數
        'host': os.getenv('DATABASE_HOST') or '',
        'user': os.getenv('DATABASE_USER') or '',
        'password': os.getenv('DATABASE_PASSWORD') or '',
        'database': os.getenv('DATABASE_USE') or '',
        'charset': os.getenv('DATABASE_CHARSET') or ''
    }

    AI_CONFIG = {
        'gemini_api_key': os.getenv('GEMINI_API_KEY') or '',
        'gemini_model': os.getenv('GEMINI_MODEL') or 'gemini-1.5-flash-002'
    }



    # Email 配置
    MAIL_SERVER = 'smtp.gmail.com'  # 或其他郵件服務商
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'alansu20051010@gmail.com'
    MAIL_PASSWORD = '0000'  # 使用應用密碼，不是帳密
    MAIL_DEFAULT_SENDER = 'alansu20051010@gmail.com'