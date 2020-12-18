import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List

from cme.extraction import extract_communication_model
from cme.data.json_parse import read_transcripts_json
from cme.domain import SessionMetadata, InteractionCandidate, MDB, Faction, Transcript
from cme import utils, database

from cme.domain import Faction, MDB

logger = logging.getLogger("cme.controller")


def update_mdbs_from_crawler(file: Path):
    try:
        if file:
            persons = json.loads(open(file.absolute(), "r").read())
        else:
            persons = database.get_crawler_db()["person"].find({})
    except:
        raise ConnectionError("Can't connect to remote crawler db. If you're developing locally you must specify a equivalent "
              "json with --file as fallback.")

    for p in persons:
        memberships = []
        for timeframe in p["fraktionen"]:
            austrittsdatum = None
            if 'austrittsDatum' in timeframe:
                austrittsdatum = get_safe_datetime(timeframe['austrittsDatum'])

            eintrittsdatum = get_safe_datetime(timeframe['eintrittsDatum'])
            membership = (eintrittsdatum, austrittsdatum, Faction.from_mdb_description(timeframe["beschreibung"]))

            memberships.append(membership)

        # will auto create MDB if not yet existent
        MDB.find_and_add_in_storage(p['vorname'], p['nachname'], memberships, p['_id'],
                                    get_safe_datetime(p['geburtsdatum']), p['geburtsort'], p['titel'], p['beruf'],
                                    initial=True)


def get_safe_datetime(date):
    if not isinstance(date, datetime):
        date = datetime.fromisoformat(date)
    return date


def init_mdb_collection(file: Path):
    database.delete_many("mdb", {})
    update_mdbs_from_crawler(file)


def evaluate_newest_sessions(id_list: List[str]):
    for id in id_list:
        transcripts = []
        current_session = utils.get_crawled_session(id)
        if not current_session:
            logging.warning(f"Could not find the session '{id}' in crawler DB. Won't update...")
            return

        file_content = read_transcripts_json(current_session)
        for metadata, inter_candidates in file_content:
            transcript = Transcript.from_interactions(
                metadata=metadata,
                interactions=extract_communication_model(inter_candidates))

            transcripts.append(transcript)

            # write to DB
            if len(transcript.interactions) == 0:
                logging.warning(f"Could not find any interactions in session with id '{id}'")
            else:
                session_id = str(transcript.session_no)
                logging.info(f"Inserting evaluated session '{session_id}' with {len(transcript.interactions)} interactions into DB")

                transcript_dict = transcript.dict()
                transcript_dict['session_id'] = session_id
                database.update_one("session", {"session_id": session_id}, transcript_dict)

    utils.notify_sentiment_analysis_group(id_list)
