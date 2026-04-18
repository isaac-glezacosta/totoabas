import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "hackathon_db")
FISH_READINGS_COLLECTION = os.getenv(
	"FISH_READINGS_COLLECTION",
	os.getenv("COLLECTION_NAME", "fish_readings")
)
FISH_STATUS_COLLECTION = os.getenv("FISH_STATUS_COLLECTION", "fish_status")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")