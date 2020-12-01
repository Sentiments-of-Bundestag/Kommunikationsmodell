from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_200_OK

from cme import utils
from cme.domain import Faction

router = APIRouter()
security = HTTPBasic()


@router.get("/faction", status_code=HTTP_200_OK, tags=['data'])
async def get_factions(credentials: HTTPBasicCredentials = Depends(security)):
    utils.get_basic_auth_client(credentials)

    factions = {}
    for faction in Faction:
        factions[faction.value] = {
            "id": faction._possible_names[0],
            "possible_names": faction._possible_names
        }
    return factions
