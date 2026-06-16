from app.db import get_db_connection

class ProductModel:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM product WHERE is_deleted = 0")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return products

    @staticmethod
    def get_by_id(product_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM product WHERE id = %s AND is_deleted = 0", (product_id,))
        product = cursor.fetchone()
        cursor.close()
        conn.close()
        return product

    @staticmethod
    def soft_delete(product_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE product SET is_deleted = 1, is_active = 0 WHERE id = %s", (product_id,))
        conn.commit()
        cursor.close()
        conn.close()
