import argparse
import json
import logging
from pathlib import Path

from cme.data import read_xml_transcript
from cme.extraction import extract_communication_model


logging.basicConfig(level=logging.INFO)


def manual_mode(args):
    for file in args.files:
        logging.info("reading \"{}\" now...".format(file.as_posix()))
        transcript = read_xml_transcript(file)
        logging.info("extracting communication model now...".format(file.as_posix()))
        interactions, f_map, s_map = extract_communication_model(transcript["interactions"])
        transcript["interactions"] = interactions
        transcript["factions"] = f_map
        transcript["speakers"] = s_map

        with open(file.with_suffix(".json"), "w", encoding="utf-8") as o:
            json.dump({"transcripts": [transcript]}, o, indent=4, ensure_ascii=False)


def server_mode(args):
    print("not implemented yet :(")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    manual_parser = subparsers.add_parser("manual", aliases=["m"])
    manual_parser.add_argument("files", nargs="+", type=Path)
    manual_parser.set_defaults(func=manual_mode)

    server_parser = subparsers.add_parser("server", aliases=["s"])
    server_parser.set_defaults(func=server_mode)

    args = parser.parse_args()

    if len(vars(args)) == 0:
        parser.error("You must choose one of the subcommands!")

    args.func(args)


if __name__ == "__main__":
    main()

