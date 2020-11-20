import logging
import asyncio
import utils

from cme import database

db = database.get_db()
collection = "mdb"

async def get_mdb(id):
    """
    Search database of MDBs by ID

    Parameters
    ----------
    arg1 : int
        The id to get the MDB. Uses the database id (not Stammdaten)

    Returns
    -------
    dictionary
        A dict that contains all data we have regarding that MDB.

    """
    mdb = await database.find_one(collection, {'id': 1})
    print(mdb)

    logging.info(mdb)
    return mdb




# search mdb by
#   * name
#   * party
#   * term
#   * date
# return mdb id
async def search_mdb(firstName, lastName, **kwargs):
    # search in db
    session = await database.find_one(collection, {'id': 1})
    # print("before_logging")
    print(session)
    logging.info(session)

# 
def create_if_not_existent(firstName, lastName, term, birthdate, faction, date):
    # 1. search_mdb
    # if found, return id
    # if not found, create new and return id
    print("test")




utils.run_async(get_mdb("1234"))
utils.run_async(search_mdb("1"))
