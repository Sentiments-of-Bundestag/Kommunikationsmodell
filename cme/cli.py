import argparse
import json
import logging
from pathlib import Path

import uvicorn

from cme.data import read_xml_transcript
from cme.extraction import extract_communication_model
from cme import utils, database


database.get_db()
logging.basicConfig(level=logging.INFO)


def manual_mode(args):
    for file in args.files:
        logging.info("reading \"{}\" now...".format(file.as_posix()))

        if file.suffix.lower() == ".json":
            with file.open("r") as f:
                # todo: implement this
                content = json.load(f)
                pass
        else:
            transcript = read_xml_transcript(file)
            logging.info("extracting communication model now...".format(file.as_posix()))
            interactions, f_map, s_map = extract_communication_model(transcript["interactions"])
            transcript["interactions"] = interactions
            transcript["factions"] = f_map
            transcript["speakers"] = s_map

        # TODO: only insert interactions, skip factions & speakers
        session_id = utils.get_session_id_safe(
            str(transcript['legislative_period']),
            str(transcript['session_no']))
        utils.run_async(database.update_one(
            "session", {"session_id": session_id}, transcript))

        with open(file.with_suffix(".json"), "w", encoding="utf-8") as o:
            json.dump({"transcripts": [transcript]}, o, indent=4, ensure_ascii=False)


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

