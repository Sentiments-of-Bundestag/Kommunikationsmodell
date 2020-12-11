import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Any

from cme import utils, database
from cme.domain import SessionMetadata, InteractionCandidate, MDB, Faction, Transcript
from cme.extraction import extract_communication_model
from cme.utils import build_datetime


logger = logging.getLogger("cme.json")


def evaluate_newest_sessions(id_list: List[str]):
    # todo: should this not be moved into extraction.py? as this is only to
    #  read the raw data and not to interpret it?
    # wasn't this the spot (extraction.py) were I first put it? :D (oskar)
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
                session_id = transcript.session_no
                logging.info(f"Inserting evaluated session '{session_id}' with {len(transcript.interactions)} interactions into DB")

                transcript_dict = transcript.dict()
                transcript_dict['session_id'] = session_id
                database.update_one("session", {"session_id": session_id}, transcript_dict)

                # save to file
                # with open(f"transcript_{session_id}.json", "w", encoding="utf-8") as o:
                #    o.write(transcript.json(exclude_none=True, indent=4, ensure_ascii=False))

    # todo: notify sentiment group about updated id's
        # cm = CommunicationModel(transcripts=transcripts)


def _get_candidates(topic_points: List[Dict], speaker_map: Dict[str, MDB]) -> List[InteractionCandidate]:
    candidates = list()

    for tp in topic_points:
        if tp["ablaufTyp"].lower() not in ["sitzungsbeginn", "tagesordnungspunkt"]:
            continue

        last_paragraph = None
        speeches = tp.get("reden", list())
        for sp in speeches:
            # why is this not in all objects?
            if "redeInhalt" not in sp:
                continue

            speaker = speaker_map.get(sp["rednerId"])

            if not speaker:
                logger.warning(
                    f"Speak with id {sp['rednerId']} is a active speaker in "
                    f"the json file but doesn't exist in the speaker list!")
                continue

            for sp_part in sp["redeInhalt"]:
                part_type = sp_part["typ"]
                if last_paragraph is not None and part_type.lower() == "paragraf":
                    candidates.append(InteractionCandidate(
                        speaker=speaker,
                        paragraph=last_paragraph,
                        comment=None))
                    last_paragraph = sp_part["text"]
                elif part_type.lower() == "kommentar":
                    candidates.append(InteractionCandidate(
                        speaker=speaker,
                        paragraph=last_paragraph,
                        comment=sp_part["text"]))
                    last_paragraph = None
                else:
                    last_paragraph = sp_part["text"]

    return candidates


def _convert_speaker(speaker_map: Dict[str, Dict]):
    def _fix_factions(factions) -> List[Tuple[datetime, datetime, Faction]]:
        fixed_factions = list()
        for f in factions:
            fixed_factions.append((
                build_datetime(f["eintrittsdatum"]),
                build_datetime(f["austrittsdatum"]),
                Faction.from_bundestag_od_id(f["id"])))
        return fixed_factions

    conv_map = dict()
    for k, v in speaker_map.items():

        birthday = v.get("geburtsdatum")
        if isinstance(v, str):
            birthday = datetime.fromisoformat(birthday)

        conv_map[v["_id"]] = MDB.find_in_storage(
            mdb_number=v["_id"],
            forename=v["vorname"],
            surname=v["nachname"],
            memberships=_fix_factions(v.get("fraktions", list())),
            birthday=birthday,
            birthplace=v.get("geburtsort"),
            title=v.get("title"),
            job_title=v.get("beruf", ""))

    return conv_map


def read_transcripts_json(
        transcript: Dict) \
        -> List[Tuple[SessionMetadata, List[InteractionCandidate]]]:

    def _merge_datetimes(datepart, timepart) -> datetime:
        if isinstance(datepart, datetime):
            datepart = datepart.isoformat()
        if isinstance(timepart, datetime):
            timepart = timepart.isoformat()
        date_str, _ = datepart.split("T")
        _, time_str = timepart.split("T")
        return datetime.fromisoformat(f"{date_str}T{time_str}")

    converted = list()

    speaker_map = {r["_id"]: r for r in transcript["rednerListe"]}
    speaker_map = _convert_speaker(speaker_map)
    session_elements = transcript["sitzungsverlauf"]

    metadata = SessionMetadata(
        session_no=int(transcript["_id"]),
        legislative_period=int(str(transcript["_id"])[:2]),
        start=_merge_datetimes(
            transcript["sitzungDatum"], session_elements["sitzungStart"]),
        end=_merge_datetimes(
            transcript["sitzungDatum"], session_elements["sitzungEnde"]))
    candidates = _get_candidates(session_elements["ablaufspunkte"], speaker_map)
    converted.append((metadata, candidates))

    return converted


def read_transcripts_json_file(
        file: Path) \
        -> List[Tuple[SessionMetadata, List[InteractionCandidate]]]:
    with file.open("r") as f:
        return read_transcripts_json(json.load(f))
