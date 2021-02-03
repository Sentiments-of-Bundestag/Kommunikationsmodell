import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

from cme import utils, database
from cme.domain import SessionMetadata, InteractionCandidate, MDB, Faction

logger = logging.getLogger("cme.json")


def _get_candidates(topic_points: List[Dict], speaker_map: Dict[str, MDB]) -> List[InteractionCandidate]:
    candidates = list()
    not_in_speaker_list = list()

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
                # try to get speaker through mdb_number from DB
                speaker = database.find_one('mdb', {'mdb_number': sp["rednerId"]})
                if speaker:
                    speaker = MDB(**speaker)
                    logging.info(f"Found speaker '{sp['rednerId']}' through mdb_number from our DB.")
                else:
                    if sp['rednerId'] not in not_in_speaker_list:
                        not_in_speaker_list.append(sp['rednerId'])
                    continue

            for sp_part in sp["redeInhalt"]:
                part_type = sp_part["typ"]
                if last_paragraph is not None and part_type.lower() == "paragraf":
                    candidates.append(InteractionCandidate(
                        speaker=speaker,
                        paragraph=utils.cleanup_str(last_paragraph),
                        comment=None))
                    last_paragraph = sp_part["text"]
                elif part_type.lower() == "kommentar":
                    if last_paragraph and speaker:
                        candidates.append(InteractionCandidate(
                            speaker=speaker,
                            paragraph=utils.cleanup_str(last_paragraph),
                            comment=utils.cleanup_str(sp_part["text"])))
                    last_paragraph = None
                else:
                    last_paragraph = sp_part["text"]

    logger.warning(f"Following speakers were not in the speaker list: {not_in_speaker_list}")
    return candidates


def _convert_speaker(speaker_map: Dict[str, Dict]):
    def _fix_factions(factions) -> List[Tuple[datetime, datetime, Faction]]:
        fixed_factions = list()
        for f in factions:
            austrittsdatum = None
            if 'austrittsDatum' in f:
                austrittsdatum = f["austrittsDatum"]
                if not isinstance(f["austrittsDatum"], datetime):
                    austrittsdatum = datetime.fromisoformat(f["austrittsDatum"])

            eintrittsdatum = f["eintrittsDatum"]
            if not isinstance(f["eintrittsDatum"], datetime):
                eintrittsdatum = datetime.fromisoformat(f["eintrittsDatum"])

            fixed_factions.append((
                eintrittsdatum,
                austrittsdatum,
                Faction.from_mdb_description(f["beschreibung"]).value))
        return fixed_factions

    conv_map = dict()
    for k, v in speaker_map.items():

        birthday = v.get("geburtsdatum")
        if isinstance(v, str):
            birthday = datetime.fromisoformat(birthday)

        conv_map[v["_id"]] = MDB.find_and_add_in_storage(
            mdb_number=v["_id"],
            forename=utils.cleanup_str(v["vorname"]),
            surname=utils.cleanup_str(v["nachname"]),
            memberships=_fix_factions(v.get("fraktionen", list())),
            birthday=birthday,
            birthplace=utils.cleanup_str(v.get("geburtsort")),
            title=utils.cleanup_str(v.get("title")),
            job_title=utils.cleanup_str(v.get("beruf", "")),
            created_by="jsonParse")

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
