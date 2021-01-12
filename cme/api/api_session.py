import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_200_OK

from cme import database, utils, controller
from cme.api import error

router = APIRouter()
security = HTTPBasic()


# for group 1 to give information about new protocols
@router.post("/", status_code=HTTP_200_OK, tags=[])
async def post_new_ids(ids: List[str], background_tasks: BackgroundTasks,
                       credentials: HTTPBasicCredentials = Depends(security)):
    utils.get_basic_auth_client(credentials)

    # create subprocess: background task to get new protocols and iterate over (start parser/cme)
    logging.info(f"Received update request for sessions '{ids}'")
    background_tasks.add_task(controller.evaluate_newest_sessions, ids)

    return {"details: ": f"Background task has been created to evaluate newest sessions with ids: '{ids}'"}


@router.get("/session/{session_id}", status_code=HTTP_200_OK, tags=['data'])
async def get_session(session_id: int, credentials: HTTPBasicCredentials = Depends(security)):
    utils.get_basic_auth_client(credentials)

    # id = legislative period + session eg: 19177
    session = database.find_one("session", {'session_id': session_id})

    if not session:
        error.raise_404(f"No session with id '{session_id}' was found.")
    del session['_id']
    return session


@router.get("/sessions/", status_code=HTTP_200_OK, tags=['data'])
async def get_session_ids(credentials: HTTPBasicCredentials = Depends(security)):
    utils.get_basic_auth_client(credentials)

    session_ids = database.find_all_ids('session', 'session_id')
    session_ids.sort()
    return session_ids


@router.get("/period/{legislative_period}", status_code=HTTP_200_OK, tags=['data'])
async def get_all_sessions_in_legislative_period(legislative_period: int,
                                                 credentials: HTTPBasicCredentials = Depends(security)):
    utils.get_basic_auth_client(credentials)

    sessions = database.find_many("session", {'legislative_period': legislative_period})
    if not sessions:
        error.raise_404(f"No sessions found for legislative period '{legislative_period}'.")

    for session in sessions:
        del session['_id']
    return sessions
