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
        possible_names = faction._possible_names
        showcase_name = None

        if possible_names:
            showcase_name = possible_names[0]
        factions[faction.value] = {
            "id": faction.value,
            "showcase_name": showcase_name,
            "possible_names": possible_names
        }
    return factions
