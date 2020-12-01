from fastapi import APIRouter, BackgroundTasks
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT

from cme.domain import Faction

router = APIRouter()


@router.get("/faction", status_code=HTTP_200_OK, tags=['data'])
async def get_factions():

    factions = {}
    for faction in Faction:
        factions[faction.value] = faction._possible_names[0]
    return factions