import argparse
import logging
from pathlib import Path

import uvicorn
import json

from cme import database, utils
from cme.data import read_transcript_xml_file, read_transcripts_json_file
from cme.domain import Transcript, CommunicationModel
from cme.extraction import extract_communication_model

database.get_db()
logging.basicConfig(level=logging.INFO)


def manual_mode(args):

    for file in args.files:
        logging.info("reading \"{}\" now...".format(file.as_posix()))
        transcripts = list()

        if file.suffix.lower() == ".json":
            logging.info("reading json based transcript file now...")
            file_content = read_transcripts_json_file(file)
        else:
            logging.info("reading xml based transcript file now...")
            file_content = [read_transcript_xml_file(file)]

        logging.info("extracting communication model now...".format(file.as_posix()))
        for metadata, inter_candidates in file_content:
            transcript = Transcript.from_interactions(metadata=metadata, interactions=extract_communication_model(inter_candidates))

            # insert into DB
            session_id = utils.get_session_id_safe(str(transcript.legislative_period), str(transcript.session_no))
            database.update_one("session", {"session_id": session_id}, json.loads(transcript.json(exclude_none=True, indent=4, ensure_ascii=False)))

            transcripts.append(transcript)

        cm = CommunicationModel(transcripts=transcripts)

        # TODO(ralph): I think I need to fix the following db calls after my
        #  refactoring.

        with open(file.with_suffix(".converted.json"), "w", encoding="utf-8") as o:
            o.write(cm.json(exclude_none=True, indent=4, ensure_ascii=False))


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

