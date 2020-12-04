import argparse
import json
import logging
from pathlib import Path

import uvicorn

import csv
from cme import database, utils
from cme.data import read_transcript_xml_file, read_transcripts_json_file, import_clients
from cme.domain import Transcript, CommunicationModel, MDB
from cme.extraction import extract_communication_model

logger = logging.getLogger()
logger.name = "cme"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s [%(levelname).1s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
database.get_db()


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
                session_id = utils.get_session_id_safe(str(transcript.legislative_period), str(transcript.session_no))
                database.update_one(
                    "session",
                    {
                        "session_id": session_id
                    },
                    transcript.dict(exclude_none=True))

            transcripts.append(transcript)

        cm = CommunicationModel(transcripts=transcripts)

        if args.dry_run:
            out_file: Path = file.with_suffix(".converted.json")
            logger.info("writing transcripts into {}.".format(out_file.absolute().as_posix()))
            with open(out_file, "w", encoding="utf-8") as o:
                o.write(cm.json(exclude_none=True, indent=4, ensure_ascii=False))

    # todo: rschlett debug stuff
    # mdb_storage = MDB._mdb_runtime_storage
    # with open("all_mdbs.json", "w") as f:
    #     json.dump(mdb_storage, f, ensure_ascii=False, indent=4)
    #     print(f"found {len(mdb_storage)} mdb entries")
    # strange_chars = utils.find_non_ascii_chars(mdb_storage)
    # for char in strange_chars:
    #     print(
    #         "repr:", char,
    #         "unicode escape:", char.encode("raw_unicode_escape"))

    if args.export_mdbs:
        filename = "mdbs_debug.csv"
        mdbs = database.find_many("mdb", {})
        mdbs = [(v['forename'], v['surname']) for v in mdbs]
        # mdbs = [(utils.cleanup_str(v['forename']), utils.cleanup_str(v['surname'])) for v in mdbs]
        from cme.utils import find_non_ascii_chars
        strange_chars = find_non_ascii_chars(mdbs)
        for char in strange_chars:
            print(
                "repr:", char,
                "unicode escape:", char.encode("raw_unicode_escape"))

        with open(filename, "w", encoding="utf-8") as o:
            w = csv.writer(o, quotechar="\"", quoting=csv.QUOTE_ALL)
            w.writerow(["forename", "surname"])
            w.writerows(mdbs)
            logger.info(f"{filename} exported")


def server_mode(args):
    uvicorn_kwargs = {
        "host": args.host,
        "port": args.port,
        "log_level": args.log_level,
        "reload": args.reload
    }

    uvicorn.run("cme.api.api:app", **uvicorn_kwargs)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    parser.add_argument(
        "--log_level",
        default="info",
        type=str,
        choices=["info", "debug", "warning"])

    manual_parser = subparsers.add_parser("manual", aliases=["m"])
    manual_parser.add_argument("files", nargs="+", type=Path)
    manual_parser.add_argument("--dry-run", default=False, action="store_true")
    manual_parser.add_argument("--export-mdbs", default=False, action="store_true")
    manual_parser.add_argument("--add-debug-objects", default=False, action="store_true")
    manual_parser.set_defaults(func=manual_mode)

    server_parser = subparsers.add_parser("server", aliases=["s"])
    server_parser.add_argument("--host", default="127.0.0.1", type=str)
    server_parser.add_argument("--port", default="9001", type=int)
    server_parser.add_argument("--reload", default=False, action="store_true")
    server_parser.set_defaults(func=server_mode)

    args = parser.parse_args()

    if len(vars(args)) == 0:
        parser.error("You must choose one of the subcommands!")

    args.func(args)


if __name__ == "__main__":
    main()
