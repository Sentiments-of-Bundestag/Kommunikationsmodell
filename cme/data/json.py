import json
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Tuple

from cme import utils, database
from cme.extraction import extract_communication_model
from cme.domain import SessionMetadata, InteractionCandidate, MDB, Faction,  Transcript, CommunicationModel
from cme.utils import build_datetime


def evaluate_newest_sessions(id_list: List[str]):
    # todo: should this not be moved into extraction.py? as this is only to
    #  read the raw data and not to interpret it?
    # wasn't this the spot (extraction.py) were I first put it? :D (oskar)
    for id in id_list:
        transcripts = []
        current_session = utils.get_crawled_session(id)
        file_content = read_transcripts_json(current_session)

        # todo: when real DB access happens, we should probably only retrieve one session per request?
        # then every transcript should be one session and should be stored in DB, (for loop should not be necessary anymore)
        for metadata, inter_candidates in file_content:
            transcript = Transcript.from_interactions(
                metadata=metadata,
                interactions=extract_communication_model(inter_candidates))

            transcripts.append(transcript)

            # write to DB
            if len(transcript.interactions) > 0:
                session_id = utils.get_session_id_safe(str(transcript.legislative_period), str(transcript.session_no))
                logging.info(f"Inserting evaluated session '{session_id}' into DB")

                # todo: change janky conversion
                transcript_dict = transcript.dict()
                #transcript_dict = json.loads(transcript.json(exclude_none=True, indent=4, ensure_ascii=False))
                transcript_dict['session_id'] = session_id
                database.update_one("session", {"session_id": session_id}, transcript_dict)

                # save to file
                #with open(f"transcript_{session_id}.json", "w", encoding="utf-8") as o:
                #    o.write(transcript.json(exclude_none=True, indent=4, ensure_ascii=False))


        #cm = CommunicationModel(transcripts=transcripts)


def _get_candidates(topic_points: List[Dict], speaker_map: Dict[str, MDB]) -> List[InteractionCandidate]:
    candidates = list()

    for tp in topic_points:
        if tp["ablauf_typ"] not in ["sitzungsbeginn", "tagesordnungspunkt"]:
            continue

        last_paragraph = None
        speeches = tp.get("reden", list())
        for sp in speeches:
            # why is this not in all objects?
            if "rede_teil" not in sp:
                continue

            speaker = speaker_map[sp["redner_id"]]

            for sp_part in sp["rede_teil"]:
                part_type = sp_part["typ"]
                if last_paragraph is not None and part_type == "Paragraf":
                    candidates.append(InteractionCandidate(
                        speaker=speaker,
                        paragraph=last_paragraph,
                        comment=None))
                    last_paragraph = sp_part["text"]
                elif part_type == "Kommentar":
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
        conv_map[v["id"]] = MDB.find_in_storage(
            mdb_number=v["id"],
            forename=v["vorname"],
            surname=v["nachname"],
            memberships=_fix_factions(v.get("fraktions", list())),
            birthday=build_datetime(v.get("geburtsdatum")),
            birthplace=v.get("geburtsort"),
            title=v.get("title"),
            job_title=v.get("beruf", ""))

    return conv_map


def read_transcripts_json(
        content: Dict) \
        -> List[Tuple[SessionMetadata, List[InteractionCandidate]]]:

    converted = list()

    for period in content.get("wahlperiode", list()):
        for transcript in period.get("protokolls", list()):
            # why do we even get a list of objects instead of a dict (╯°□°)╯︵ ┻━┻
            speaker_map = {r["id"]: r for r in transcript["redner_liste"]}
            speaker_map = _convert_speaker(speaker_map)

            session_elements = transcript["sitzungsverlauf"]

            metadata = SessionMetadata(
                session_no=int(transcript["id"]),
                legislative_period=int(period["id"]),
                start=build_datetime(
                    transcript["sitzung_datum"],
                    session_elements["sitzung_start"]),
                end=build_datetime(
                    transcript["sitzung_datum"],
                    session_elements["sitzung_ende"]))

            candidates = _get_candidates(session_elements["ablaufspunkte"], speaker_map)
            converted.append((metadata, candidates))

    return converted


def read_transcripts_json_file(
        file: Path) \
        -> List[Tuple[SessionMetadata, List[InteractionCandidate]]]:

    with file.open("r") as f:
        return read_transcripts_json(json.load(f))


