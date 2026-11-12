import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=5000)
print(client.admin.command("ping"))