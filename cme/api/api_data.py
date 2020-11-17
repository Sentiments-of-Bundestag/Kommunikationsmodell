from fastapi import APIRouter, BackgroundTasks
from starlette.status import HTTP_200_OK, HTTP_204_NO_CONTENT
from typing import List
import logging

from cme import database
from cme.api import error
from cme.data import json

router = APIRouter()
db = database.get_db()


# for group 1 to give information about new protocols
@router.post("/", status_code=HTTP_200_OK, tags=[])
async def post_new_ids(ids: List[str], background_tasks: BackgroundTasks):
    # create subprocess: background task to get new protocols and iterate over (start parser/cme)
    logging.info(f"Received update request for sessions '{ids}'")
    background_tasks.add_task(json.evaluate_newest_sessions, ids)

    return {"Message: ": f"Background task has been created to evaluate newest sessions with ids: '{ids}'"}


@router.get("/session/{session_id}", status_code=HTTP_200_OK, tags=['data'])
async def get_session(session_id: str):
    # id = legislative period + session eg: 19177
    session = database.find_one("session", {'session_id': session_id})

    if not session:
        error.raise_404(f"No session with id '{session_id}' was found.")
    del session['_id']
    return session


@router.get("/sessions/{legislative_period}", status_code=HTTP_200_OK, tags=['data'])
async def get_all_sessions_in_legislative_period(legislative_period: int):
    # todo: add pagination
    # id = legislative period: 19
    sessions = database.find_many("session", {'legislative_period': legislative_period})
    if not sessions:
        error.raise_404(f"No sessions found for legislative period '{legislative_period}'.")

    for session in sessions:
        del session['_id']
    return sessions





# optional endpoints for users & factions:
# accept new mdb stammdaten?
# get users by birth range
# get users for legislative period