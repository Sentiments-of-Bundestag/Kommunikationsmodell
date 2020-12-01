from fastapi import APIRouter, BackgroundTasks
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from cme import database
from cme.api import error

router = APIRouter()


@router.get("/mdb", status_code=HTTP_200_OK, tags=['data'])
async def get_session(id: str = "",
                      speaker_id: str = "",
                      forename: str = "",
                      surname: str = ""
                      ):
    query = {}
    # unique identifier, so only one object should be returned
    if id != "":
        return database.find_many("mdb", {"_id": id})
    if speaker_id != "":
        return database.find_many("mdb", {"speaker_id": id})

    # search by multiple params
    if forename != "":
        query['forename'] = forename
    if surname != "":
        query['surname'] = surname
    users = database.find_many("mdb", query)
    return users