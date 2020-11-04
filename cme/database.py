from datetime import datetime, timezone
import asyncio
from typing import List
import uuid
from collections import namedtuple

import motor.motor_asyncio

db = None
DB_USER = None
DB_PASSWORD = None
DB_HOST_PORT = "localhost:27017"
DB_DB = "cm_data"


def get_db():
    global db
    if db:
        return db

    # create DB connection string with or without user authentication
    if DB_USER:
        db_url = f"mongodb://{DB_USER}:{DB_PASSWORD}@{DB_HOST_PORT}/?authSource={DB_DB}"
    else:
        db_url = f"mongodb://{DB_HOST_PORT}/{DB_DB}"

    client = motor.motor_asyncio.AsyncIOMotorClient(db_url, tz_aware=True)
    db = client[DB_DB]
    return db


async def find_one(collection_name: str, query: dict) -> dict:
    return await db[collection_name].find_one(query)


async def find_many(collection_name: str, query: dict) -> list:
    cursor = db[collection_name].find(query)
    return await cursor.to_list(None)


async def insert_many(collection_name: str, query: list) -> None:
    collection = db[collection_name]
    await collection.insert_many(query)


async def update_one(collection_name: str, query: dict, update: dict, on_insert=None):
    if on_insert is None:
        on_insert = {}
    now = datetime.utcnow().isoformat()
    update['modified'] = now
    on_insert['created'] = now
    result = await db[collection_name].update_one(query, {'$set': update, '$setOnInsert': on_insert}, upsert=True)
    if result.modified_count == 1:
        return True
    return False