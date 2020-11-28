import logging
import os
from datetime import datetime

from pymongo import MongoClient
import motor.motor_asyncio
from pymongo.errors import ServerSelectionTimeoutError

db = None

DB_USER = os.environ.get("DB_MONGO_STD_USERNAME")
DB_PASSWORD = os.environ.get("DB_MONGO_STD_PASSWORD")
DB_HOST_PORT = "cme_mongodb:27017"
DB_DB = "cme_data"

crawl_db = None

def get_db():
    global db
    if db:
        return db

    # create DB connection string with or without user authentication
    if DB_USER:
        db_url = f"mongodb://{DB_USER}:{DB_PASSWORD}@{DB_HOST_PORT}/?authSource={DB_DB}"
    else:
        db_url = f"mongodb://{DB_HOST_PORT}/{DB_DB}"

    client = MongoClient(db_url, tz_aware=True)
    db = client[DB_DB]
    return db


def get_crawler_db():
    global crawl_db
    if crawl_db:
        return crawl_db

    # check for env vars
    user = os.environ.get("CRAWL_DB_USER")
    pw = os.environ.get("CRAWL_DB_PASSWORD")
    crawl_ip = os.environ.get("CRAWL_DB_IP")
    db_name = "test"

    if not user or not pw or not crawl_ip:
        logging.error(
            "Please provide CRAWL_DB_USER, CRAWL_DB_PASSWORD and CRAWL_DB_IP as env var's to access crawler DB.")
        return None

    db_url = f"mongodb://{user}:{pw}@{crawl_ip}/{db_name}"
    try:
        client = MongoClient(db_url, tz_aware=True, serverSelectionTimeoutMS=10000)
        crawl_db = client[db_name]

        # test connection
        collections = crawl_db.list_collection_names()
        print(collections)

        logging.info(f"Connection to external DB was successful.")
        return crawl_db
    except ServerSelectionTimeoutError as err:
        logging.error(f"Timeout while connecting to external DB, error: {err}")
    return None


def find_one(collection_name: str, query: dict) -> dict:
    return db[collection_name].find_one(query)


def find_all_ids(collection_name: str, attribute_name: str):
    result = db[collection_name].find({}, {attribute_name: 1})
    return [session['session_id'] for session in result]


def find_many(collection_name: str, query: dict) -> list:
    cursor = db[collection_name].find(query)
    list = []
    for item in cursor:
        list.append(item)
    return list


def insert_many(collection_name: str, query: list) -> None:
    collection = db[collection_name]
    collection.insert_many(query)


def update_one(collection_name: str, query: dict, update: dict, on_insert=None):
    if on_insert is None:
        on_insert = {}
    now = datetime.utcnow().isoformat()
    update['modified'] = now
    on_insert['created'] = now
    result = db[collection_name].update_one(query, {'$set': update, '$setOnInsert': on_insert}, upsert=True)
    if result.modified_count == 1:
        return True
    return False

