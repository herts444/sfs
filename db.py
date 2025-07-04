# db.py
import os
from dotenv import load_dotenv
from datetime import datetime
import pymongo

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "onlyfans_posts")

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["post_links"]

def save_post_link(post_url, profile_id):
    """
    Сохраняет ссылку на пост в MongoDB.
    Каждый документ содержит поле post_url, profile_id и дату создания.
    """
    try:
        document = {
            "post_url": post_url,
            "profile_id": profile_id,  # добавляем идентификатор профиля
            "created_at": datetime.utcnow()
        }
        result = collection.insert_one(document)
        print(f"Ссылка сохранена, id документа: {result.inserted_id}")
        return True
    except Exception as e:
        print(f"Ошибка при сохранении в MongoDB: {e}")
        return False
