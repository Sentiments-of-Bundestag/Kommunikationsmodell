import logging
import os
from datetime import datetime
from typing import Tuple

from pymongo import MongoClient
from pymongo.database import Database as MongoDatabase
from pymongo.errors import ServerSelectionTimeoutError

logger = logging.getLogger("cme.database")

__cme_client = None
__cme_db = None
__crawler_client = None
__crawler_db = None


def _open_db_connection(
        user: str,
        password: str,
        address: str,
        db_name: str,
        auth_db_name: str = None,
        test_connection: bool = True) \
        -> Tuple[MongoClient, MongoDatabase]:
    logger.info(f"trying to connect to mongo db {address}")

    if not auth_db_name:
        auth_db_name = "admin"

    if user:
        db_url = f"mongodb://{user}:{password}@{address}/?authSource={auth_db_name}"
    else:
        db_url = f"mongodb://{address}/{db_name}"

    client = MongoClient(db_url, tz_aware=True, serverSelectionTimeoutMS=10000)
    db = client[db_name]

    if test_connection:
        try:
            collections = db.list_collection_names()
            logger.info(f"Connection to DB with address '{address}' was successful.")
        except ServerSelectionTimeoutError as err:
            logging.error(f"Timeout while connecting to external DB, error: {err}")
            raise RuntimeError(
                f"Connecting to db {address} failed! Please check the "
                f"used credentials.")

    return client, db


def _get_credentials(
        username_key,
        password_key,
        address_key,
        db_name_key) \
        -> Tuple[str, str, str, str]:
    username = os.getenv(username_key)
    password = os.getenv(password_key)
    address = os.getenv(address_key)
    db_name = os.getenv(db_name_key)

    return username, password, address, db_name


def _generic_get_db(
        prefix: str,
        use_default_auth_db: bool = True) \
        -> Tuple[MongoClient, MongoDatabase]:
    credentials = _get_credentials(
        f"{prefix}_DB_USERNAME",
        f"{prefix}_DB_PASSWORD",
        f"{prefix}_DB_ADDRESS",
        f"{prefix}_DB_NAME")

    username = credentials[0]
    password = credentials[1]
    address = credentials[2]
    db_name = credentials[3]

    auth_db = db_name
    if use_default_auth_db:
        auth_db = "admin"

    return _open_db_connection(username, password, address, db_name, auth_db)


def get_cme_db() -> MongoDatabase:
    global __cme_db
    global __cme_client
    if __cme_db:
        return __cme_db

    __cme_client, __cme_db = _generic_get_db("CME", False)
    return __cme_db


def get_crawler_db() -> MongoDatabase:
    global __crawler_db
    global __crawler_client
    if __crawler_db:
        return __crawler_db

    __crawler_client, __crawler_db = _generic_get_db("CRAWLER")
    return __crawler_db


def find_one(collection_name: str, query: dict, exclude: dict = None) -> dict:
    db = get_cme_db()
    if exclude:
        return db[collection_name].find_one(query, exclude)
    return db[collection_name].find_one(query)


def find_all_ids(collection_name: str, attribute_name: str):
    db = get_cme_db()
    result = db[collection_name].find({}, {attribute_name: 1})
    return [session['session_id'] for session in result]


def find_many(collection_name: str, query: dict, exclude: dict = None) -> list:
    db = get_cme_db()
    if exclude:
        cursor = db[collection_name].find(query, exclude)
    else:
        cursor = db[collection_name].find(query)
    list = []
    for item in cursor:
        list.append(item)
    return list


def insert_many(collection_name: str, query: list) -> None:
    db = get_cme_db()
    collection = db[collection_name]
    collection.insert_many(query)


def update_one(collection_name: str, query: dict, update: dict, on_insert=None):
    db = get_cme_db()
    if on_insert is None:
        on_insert = {}
    now = datetime.utcnow().isoformat()
    update['modified'] = now
    on_insert['created'] = now
    result = db[collection_name].update_one(query, {'$set': update, '$setOnInsert': on_insert}, upsert=True)
    if result.modified_count == 1:
        return True
    return False


def delete_many(collection_name: str, query: dict):
    db = get_cme_db()
    collection = db[collection_name]
    collection.delete_many(query)
