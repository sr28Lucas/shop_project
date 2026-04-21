import os
from dotenv import load_dotenv
from pathlib import Path


# 載入 .env 檔案中的變數
dotenv_path = Path(__file__).resolve().parent / '..' / '.env.txt'
load_dotenv(dotenv_path = dotenv_path) 


class config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret_key' #加密金鑰 要這才可以用flask的加密功能
    SQLALCHEMY_TRACK_MODIFICATIONS = False #某個看不懂但應該用不到的功能 開了似乎會吃效能
    DB_CONFIG = { #資料庫參數
        'host': os.getenv('DATABASE_HOST') or '',
        'user': os.getenv('DATABASE_USER') or '',
        'password': os.getenv('DATABASE_PASSWORD') or '',
        'database': os.getenv('DATABASE_USE') or '',
        'charset': os.getenv('DATABASE_CHARSET') or ''
    }


