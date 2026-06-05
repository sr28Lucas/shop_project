import re

class Validator:
    @staticmethod
    def is_valid_email(email):
        if not email or len(email) > 100:
            return False
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_regex, email) is not None

    @staticmethod
    def is_valid_name(name):
        return name and 1 <= len(name) <= 30

    @staticmethod
    def is_valid_phone(phone):
        if not phone:
            return True # 電話通常是可選的
        # 簡單檢查數字與長度
        clean_phone = re.sub(r'[\s\-()]', '', phone)
        return 8 <= len(clean_phone) <= 20

    @staticmethod
    def is_valid_address(address):
        if not address:
            return True # 地址可能是可選的
        return 5 <= len(address) <= 100

    @staticmethod
    def is_valid_password(password):
        return password and len(password) >= 4
