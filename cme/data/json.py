from typing import List

from cme import utils, database
from cme.extraction import extract_communication_model


def read_json_transcript(current_session):
    # todo: implement me
    pass


def evaluate_newest_sessions(id_list: List[str]):
    for id in id_list:
        current_session = utils.get_crawled_session(id)
        transcript = read_json_transcript(current_session)
        interactions, f_map, s_map = extract_communication_model(transcript["interactions"])
        transcript["interactions"] = interactions
        transcript["factions"] = f_map
        transcript["speakers"] = s_map

        session_id = utils.get_session_id_safe(str(transcript['legislative_period']), str(transcript['session_no']))
        utils.run_async(database.update_one("session", {"session_id": session_id}, transcript))
