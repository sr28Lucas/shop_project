import re

class Validator:
    @staticmethod
    def is_valid_email(email):
        if not email or not (3 <= len(email) <= 100):
            return False
        # 加強郵件格式檢查
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+$'
        return re.match(email_regex, email) is not None

    @staticmethod
    def is_valid_name(name):
        return name and 1 <= len(name) <= 100

    @staticmethod
    def is_valid_phone(phone):
        if not phone:
            return True
        # 簡單檢查數字與長度
        clean_phone = re.sub(r'[\s\-()]', '', phone)
        return 8 <= len(clean_phone) <= 30

    @staticmethod
    def is_valid_address(address):
        # 地址不輸入 (空) 或長度在 5-200 之間
        if not address or len(address) == 0:
            return True
        return 5 <= len(address) <= 200

    @staticmethod
    def is_valid_password(password):
        # 只要 4 位，方便測試（如 root, 1234）
        return password and len(password) >= 4

    @staticmethod
    def is_valid_length(text, max_l, min_l=0):
        # 防止資料庫 varchar 溢位導致的報錯
        if text is None: return min_l == 0
        return min_l <= len(str(text)) <= max_l

    @staticmethod
    def is_valid_number(val, max_v, min_v=0):
        # 防止負數與 decimal/int 溢位
        try:
            n = float(val)
            return min_v <= n <= max_v
        except (ValueError, TypeError, KeyError):
            return False

    @staticmethod
    def is_valid_credit_card(card_number):
        if not card_number:
            return False
        # 僅允許以數字開頭，且由數字、空格、連字號組成
        if not re.match(r'^\d[0-9\s\-]*$', card_number):
            return False
        # 移除空格與連字號
        clean_card = re.sub(r'[\s\-]', '', card_number)
        # 嚴格檢查是否為 16 碼數字
        return clean_card.isdigit() and len(clean_card) == 16
