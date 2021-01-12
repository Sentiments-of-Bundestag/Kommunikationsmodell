import argparse
import json
import logging
import os
from pathlib import Path

import uvicorn

import csv

from dotenv import load_dotenv

from cme import database, utils
from cme.data import read_transcript_xml_file, read_transcripts_json_file, import_clients
from cme.domain import Transcript, CommunicationModel, MDB
from cme.extraction import extract_communication_model
from cme.utils import safe_json_dumps, safe_json_dump
from cme.controller import update_mdbs_from_crawler, init_mdb_collection

logger = logging.getLogger()
logger.name = "cme"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s [%(levelname).1s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


def manual_mode(args):
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
                logger.info("writing transcript into db.")
                database.update_one(
                    "session",
                    {
                        "session_id": transcript.session_no
                    },
                    transcript.dict(exclude_none=True, exclude_unset=True))

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


def initialize(args):
    init_mdb_collection(args.file)


def server_mode(args):
    uvicorn_kwargs = {
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "reload": args.reload,
    }

    if args.env_file:
        uvicorn_kwargs["env_file"] = args.env_file

    uvicorn.run("cme.api.api:app", **uvicorn_kwargs)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--env-file", type=Path, default=Path.cwd() / ".env")
    parser.add_argument(
        "--log_level",
        default="info",
        type=str,
        choices=["info", "debug", "warning"])

    subparsers = parser.add_subparsers()

    manual_parser = subparsers.add_parser("manual", aliases=["m"])
    manual_parser.add_argument("files", nargs="+", type=Path)
    manual_parser.add_argument("--dry-run", default=False, action="store_true")
    manual_parser.add_argument("--add-debug-objects", default=False, action="store_true")
    manual_parser.add_argument("--notify", default=False, action="store_true")
    manual_parser.set_defaults(func=manual_mode)

    dump_parser = subparsers.add_parser("dump", aliases=["d"])
    dump_parser.add_argument("--database", type=str, default="cme", choices=["cme", "crawler"])
    dump_parser.add_argument("--index-field", type=str, default="_id")
    dump_parser.add_argument("--index", type=str, default="")
    dump_parser.add_argument("--list-collections", default=False, action="store_true")
    dump_parser.add_argument("--list-collection-fields", default=False, action="store_true")
    dump_parser.add_argument("--collection", type=str)
    dump_parser.add_argument("--output-file", type=Path)
    dump_parser.set_defaults(func=dump_mode)

    server_parser = subparsers.add_parser("server", aliases=["s"])
    server_parser.add_argument("--host", default="127.0.0.1", type=str)
    server_parser.add_argument("--port", default="9001", type=int)
    server_parser.add_argument("--reload", default=False, action="store_true")
    server_parser.set_defaults(func=server_mode)

    init_parser = subparsers.add_parser("init", aliases=["i"], help="Generates a new mdb collection locally from the crawler db (default) or file (see --file)")
    init_parser.add_argument("--file", type=Path, help="Path of a json you want to use instead of the remote crawler")
    init_parser.set_defaults(func=initialize)

    args = parser.parse_args()

    if not args.env_file.exists() or not args.env_file.is_file():
        logger.warning(
            "You are missing the --env-file argument and your current "
            "working directory does not contain a .env file. Continuing "
            "without it but this requires that you set the environment "
            "variables yourself!")
        args.env_file = None

    if args.env_file:
        load_dotenv(args.env_file)

    if len(vars(args)) == 0:
        parser.error("You must choose one of the subcommands!")

    args.func(args)


if __name__ == "__main__":
    main()
