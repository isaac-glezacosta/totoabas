from pymongo import MongoClient
from app.config import MONGO_URI, DB_NAME, FISH_READINGS_COLLECTION, FISH_STATUS_COLLECTION

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
fish_readings_collection = db[FISH_READINGS_COLLECTION]
fish_status_collection = db[FISH_STATUS_COLLECTION]