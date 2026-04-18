import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "hackathon_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "measurements")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")