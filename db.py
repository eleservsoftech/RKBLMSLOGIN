

# mongodb

# Libraries to install:
# pip install pymongo "pydantic[email]"

# database.py
# Libraries to install:
# pip install pymongo

from pymongo import MongoClient
from dotenv import load_dotenv
import os

# --- Load Environment Variables ---
load_dotenv()  # Loads variables from .env file into environment

# --- Get credentials from environment ---
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_DB = os.getenv("MONGO_DB")

# --- Construct MongoDB URI ---
MONGO_DETAILS = (
    f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/"
    f"{MONGO_DB}?directConnection=true&authSource=admin"
)

# --- Database Setup ---
client = MongoClient(MONGO_DETAILS)
database = client[MONGO_DB]

# Collections
users_collection = database.get_collection("users")
logins_collection = database.get_collection("logins")
usertypes_collection = database.get_collection("usertypes")

print("MongoDB connection successful!")







