from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_200_OK

from cme import database, utils
from cme.api import error

router = APIRouter()
security = HTTPBasic()


@router.get("/mdb", status_code=HTTP_200_OK, tags=['data'])
async def get_mdb(id: str = "",
                  speaker_id: str = "",
                  forename: str = "",
                  surname: str = "",
                  credentials: HTTPBasicCredentials = Depends(security)):
    utils.get_basic_auth_client(credentials)
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
    if not users:
        error.raise_404(f"No mdb's were found for your search query: {query}")
    return users
