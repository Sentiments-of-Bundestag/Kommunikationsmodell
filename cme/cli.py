import argparse
import json
import logging
from pathlib import Path

import uvicorn

from cme import database, utils
from cme.data import read_transcript_xml_file, read_transcripts_json_file
from cme.domain import Transcript, CommunicationModel
from cme.extraction import extract_communication_model

logger = logging.getLogger()
logger.name = "cme"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s [%(levelname).1s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M')
database.get_db()


def manual_mode(args):
    #strange_chars = set()

    for file in args.files:
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

            transcript = Transcript.from_interactions(metadata=metadata, interactions=extract_communication_model(inter_candidates))

            # insert into DB
            if not args.dry_run:
                logger.info("writing transcript into db.")
                session_id = utils.get_session_id_safe(str(transcript.legislative_period), str(transcript.session_no))
                database.update_one(
                    "session",
                    {
                        "session_id": session_id
                    },
                    transcript.dict())

            transcripts.append(transcript)

        cm = CommunicationModel(transcripts=transcripts)

        #from cme.utils import find_non_ascii_chars
        #strange_chars.update(find_non_ascii_chars(transcripts))

        if args.dry_run:
            out_file: Path = file.with_suffix(".converted.json")
            logger.info("writing transcripts into {}.".format(out_file.absolute().as_posix()))
            with open(out_file, "w", encoding="utf-8") as o:
                o.write(cm.json(exclude_none=True, indent=4, ensure_ascii=False))

    #for char in strange_chars:
    #    print(
    #        "repr:", char,
    #        "unicode escape:", char.encode("raw_unicode_escape"))


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

