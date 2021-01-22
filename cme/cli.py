import argparse
import logging
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from cme.controller import init_mdb_collection, manual_import, dump_mode

logger = logging.getLogger()
logger.name = "cme"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s [%(levelname).1s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')


def start_server(args):
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

    manual_parser = subparsers.add_parser("manual", aliases=["m"],
                                          help='Manually read files for communication extraction.')
    manual_parser.add_argument("files", nargs="+", type=Path,
                               help="Path to one or more .json (from Crawler service) or .xml (from official "
                                    "Bundestag protocols) files. Must contain protocols of Bundestag.")
    manual_parser.add_argument("--dry-run", default=False, action="store_true",
                               help="Set to true if you do not want to save data into the database. (Default: False)")
    manual_parser.add_argument("--add-debug-objects", default=False, action="store_true",
                               help="While assembling communication data, save debug information (eg where the data "
                                    "comes from) into the communication objects. (Default: False)")
    manual_parser.add_argument("--notify", default=False, action="store_true",
                               help="Notify Group 3/Sentiment Analyses via HTTP request about new protocols. "
                                    "(Default: False)")
    manual_parser.set_defaults(func=manual_import)

    dump_parser = subparsers.add_parser("dump", aliases=["d"], help="Let's you extract database raw data. "
                                                                    "Useful for debugging.")
    dump_parser.add_argument("--database", type=str, default="cme", choices=["cme", "crawler"],
                             help="Specify the Database you want to dump data from (Default: cme)")
    dump_parser.add_argument("--index-field", type=str, default="_id",
                             help="Specify the index field (???). (Default: _id)")
    dump_parser.add_argument("--index", type=str, default="",
                             help=" Specify the index. (Default: id)")
    dump_parser.add_argument("--list-collections", default=False, action="store_true",
                             help="Set to true if you want to list all available collections. "
                                  "Needs the --collection option. (Default: False)")
    dump_parser.add_argument("--list-collection-fields", default=False, action="store_true",
                             help="Set to true if you want to list all collection fields. "
                                  "Needs the --collection option. (Default: False)")
    dump_parser.add_argument("--collection", type=str,
                             help="Specify the collection you want to operate on.")
    dump_parser.add_argument("--output-file", type=Path,
                             help="Specify the output file of the dump.")
    dump_parser.set_defaults(func=dump_mode)

    server_parser = subparsers.add_parser("server", aliases=["s"],
                                          help="Start the server. Includes the REST API as well as documentation.")
    server_parser.add_argument("--host", default="127.0.0.1", type=str, help="Define the host. (Default: 127.0.0.1)")
    server_parser.add_argument("--port", default="9001", type=int, help="Define the port. (Default: 9001)")
    server_parser.add_argument("--reload", default=False, action="store_true",
                               help="Set to true for reload on file change (Default: False)")
    server_parser.set_defaults(func=start_server)

    init_parser = subparsers.add_parser("init", aliases=["i"],
                                        help="Generates a new mdb collection locally from the crawler db (default) or"
                                             " file (see --file)")
    init_parser.add_argument("--file", type=Path, help="Path of a json you want to use instead of the remote crawler")
    init_parser.set_defaults(func=init_mdb_collection)

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
