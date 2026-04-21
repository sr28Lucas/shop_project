import mysql.connector
from .config import config
from datetime import datetime


def get_db_connection():
    return mysql.connector.connect(**config.DB_CONFIG)
