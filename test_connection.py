
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    print("Error: MONGO_URI not found. Check your .env file.")
else:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("Successfully connected to MongoDB Atlas!")
        print("Connection is working.")
        client.close()
    except Exception as e:
        print("Connection failed:")
        print(e)
