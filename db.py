# database.py
# database.py
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

# --- Load Environment Variables ---
load_dotenv()  # Loads variables from .env file into environment

# --- Get credentials from environment ---
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_DB = os.getenv("MONGO_DB")

# --- Properly encode username and password ---
# This is the key change to handle special characters.
encoded_user = quote_plus(MONGO_USER)
encoded_password = quote_plus(MONGO_PASSWORD)

# --- Construct MongoDB URI with encoded credentials ---
MONGO_DETAILS = (
    f"mongodb://{encoded_user}:{encoded_password}@{MONGO_HOST}:{MONGO_PORT}/"
    f"{MONGO_DB}?directConnection=true&authSource=admin"
)

# --- Database Setup ---
client = MongoClient(MONGO_DETAILS)
database = client[MONGO_DB]

# Collections
users_collection = database.get_collection("users")
logins_collection = database.get_collection("logins")
usertypes_collection = database.get_collection("usertypes")
packages_collection = database.get_collection("packages")
# Courses Collection (Assuming this exists from your previous prompt)
courses_collection = database.get_collection("courses")
# --- NEW: Collection for managing package-course bundles ---
package_bundle_collection = database.get_collection("package_bundles")

print("MongoDB connection successful!")
