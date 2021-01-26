import json
import logging
from pathlib import Path
from typing import List

from cme import utils, database
from cme.data import read_transcripts_json, read_transcripts_json_file, read_transcript_xml_file
from cme.domain import Faction, MDB
from cme.domain import Transcript, CommunicationModel
from cme.extraction import extract_communication_model
from cme.utils import get_safe_datetime, safe_json_dumps, safe_json_dump

logger = logging.getLogger("cme.controller")


def init_mdb_collection(args):
    file = args.file
    database.delete_many("mdb", {})
    update_mdbs_from_crawler(file)


def update_mdbs_from_crawler(file: Path):
    try:
        if file:
            persons = json.loads(open(file.absolute(), "r").read())
        else:
            persons = database.get_crawler_db()["person"].find({})
    except:
        raise ConnectionError(
            "Can't connect to remote crawler db. If you're developing locally you must specify a equivalent "
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


def evaluate_newest_sessions(id_list: List[str]):
    for id in id_list:
        transcripts = []
        current_session = utils.get_crawled_session(id)
        if not current_session:
            logging.warning(f"Could not find the session '{id}' in crawler DB. Won't update...")
            continue

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
                logging.info(
                    f"Inserting evaluated session '{session_id}' with {len(transcript.interactions)} interactions into DB")

                transcript_dict = transcript.dict(exclude_none=True, exclude_unset=True)
                transcript_dict['session_id'] = session_id
                database.update_one("session", {"session_id": session_id}, transcript_dict)

    utils.notify_sentiment_analysis_group(id_list)


def manual_import(args):
    if args.dry_run:
        MDB.set_storage_mode("runtime")

    files = []
    for file in args.files:
        if file.is_file():
            files.append(file)
        elif file.is_dir():
            for sub_file in list(file.iterdir()):
                if sub_file.is_file():
                    files.append(sub_file)

    for file in files:
        logger.info("reading \"{}\" now...".format(file.as_posix()))
        transcripts = list()

        if file.suffix.lower() == ".json":
            logger.info("reading json based transcript file now...")
            file_content = read_transcripts_json_file(file)
        else:
            logger.info("reading xml based transcript file now...")
            file_content = [read_transcript_xml_file(file)]

        logger.info("extracting communication model now...".format(file.as_posix()))
        for metadata, inter_candidates in file_content:

            transcript = Transcript.from_interactions(
                metadata=metadata,
                interactions=extract_communication_model(
                    candidates=inter_candidates,
                    add_debug_objects=args.add_debug_objects))

            # insert into DB
            if not args.dry_run:
                transcript_dict = transcript.dict(exclude_none=True, exclude_unset=True)
                logger.info(f"writing transcript with '{len(transcript_dict['interactions'])}' interactions into db.")
                database.update_one("session", {"session_id": transcript.session_no}, transcript_dict)

            transcripts.append(transcript)

            # notify sentiment group
            if args.notify and transcript:
                utils.notify_sentiment_analysis_group([str(transcript.session_no)])

        cm = CommunicationModel(transcripts=transcripts)

        if args.dry_run:
            out_file: Path = file.with_suffix(".converted.json")
            logger.info("writing transcripts into {}.".format(out_file.absolute().as_posix()))
            with open(out_file, "w", encoding="utf-8") as o:
                o.write(cm.json(exclude_none=True, indent=4, ensure_ascii=False))
            with open(out_file.parent / "mdb.json", "w", encoding="utf-8") as o:
                safe_json_dump(MDB._mdb_runtime_storage, o)


def dump_mode(args):
    if args.database == "crawler":
        db = database.get_crawler_db()
    else:
        db = database.get_cme_db()

    if args.list_collections:
        print(db.list_collection_names())
    elif args.list_collection_fields:
        print(list(db[args.collection].find_one().keys()))
    elif args.collection:
        if args.index:
            obj = db[args.collection].find_one({args.index_field: args.index})
            # _id is an integer so we cast
            if args.index_field == "_id":
                obj = db[args.collection].find_one({args.index_field: int(args.index)})
        else:
            obj = list()
            for doc in db[args.collection].find():
                obj.append(doc)

        if args.output_file:
            with args.output_file.open("w") as f:
                safe_json_dump(obj, f, indent=4)
        else:
            print(safe_json_dumps(obj, indent=4))
    else:
        logger.info(
            "Dump mode did nothing. This is probably not what you wanted. "
            "Please check your command line arguments and rerun the tool "
            "after doing so.")
