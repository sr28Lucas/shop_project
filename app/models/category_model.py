from app.db import get_db_connection

class CategoryModel:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM category WHERE is_deleted = 0")
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return categories

    @staticmethod
    def get_by_id(category_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM category WHERE id = %s AND is_deleted = 0", (category_id,))
        category = cursor.fetchone()
        cursor.close()
        conn.close()
        return category

    @staticmethod
    def soft_delete(category_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE category SET is_deleted = 1 WHERE id = %s", (category_id,))
        conn.commit()
        cursor.close()
        conn.close()
