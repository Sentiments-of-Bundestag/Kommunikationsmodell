import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, Tuple, Any, Set

import requests
from fastapi.security import HTTPBasicCredentials

from cme import database
from cme.api import error


def reverse_dict(dict_obj: Dict) -> Dict:
    def _rebuild_dict(potential_dict: Tuple[Tuple]):
        if isinstance(potential_dict, tuple):
            return {k: v for k, v in potential_dict}
        return potential_dict

    return {v: _rebuild_dict(k) for k, v in dict_obj.items()}


def build_datetime(date_str: str, time_str: str = None, date_order: str = "DMY") -> datetime:
    if not date_str:
        return None

    datetime_args = list()

    date_parts = date_str.split(".")
    assert len(date_parts) == 3

    datetime_args.append(int(date_parts[date_order.upper().find("Y")]))
    datetime_args.append(int(date_parts[date_order.upper().find("M")]))
    datetime_args.append(int(date_parts[date_order.upper().find("D")]))

    if time_str:
        # apparently they allow free format time fields... I mean there are time
        # data types in xml but sure, let's role with free format time fields.
        # Otherwise reading this file with a computer would be to easy I guess...
        time_sep = ":" if ":" in time_str else "."
        time_parts = [
            t if not " " in t else t[:t.find(" ")]
            for t in time_str.split(time_sep)]
        datetime_args += [int(t) for t in time_parts]

    return datetime(*datetime_args)


def build_isoformat_time_str(date_str: str, time_str: str, date_order: str = "DMY") -> str:
    return build_datetime(date_str, time_str, date_order).isoformat()


def cleanup_str(str_to_fix):
    def _replace(value, chars, replacement) -> str:
        for char in chars:
            value = value.replace(char, replacement)
        return value

    alternative_spaces = {
        u"\xa0",  # NO - BREAK SPACE
        u"\xad",  # Soft Hyphen
        u"\u1680",  # OGHAM SPACE MARK
        u"\u180e",  # MONGOLIAN VOWEL SEPARATOR
        u"\u2000",  # EN QUAD
        u"\u2001",  # EM QUAD
        u"\u2002",  # EN SPACE
        u"\u2003",  # EM SPACE
        u"\u2004",  # THREE - PER - EM SPACE
        u"\u2005",  # FOUR - PER - EM SPACE
        u"\u2006",  # SIX - PER - EM SPACE
        u"\u2007",  # FIGURE SPACE
        u"\u2008",  # PUNCTUATION SPACE
        u"\u2009",  # THIN SPACE
        u"\u200a",  # HAIR SPACE
        u"\u2028",  # LINE SEPARATOR
        u"\u2029",  # PARAGRAPH SEPARATOR
        u"\u202f",  # NARROW NO - BREAK SPACE
        u"\u205f",  # MEDIUM MATHEMATICAL SPACE
        u"\u3000"  # IDEOGRAPHIC SPACE
    }

    alternative_dashes = {
        u"\u2011",  # Non-Breaking Hyphen
        u"\u2012",  # Figure Dash
        # we are keeping \u2013 for the moment as those are used for the
        # comment separation by the bundestag in the files
        # u"\u2013",  # En Dash
    }

    alt_double_quotes = {
        u"\u201c",
        u"\u201e",
    }

    alt_single_quotes = {
        u"\u2018",
        u"\u2019",
        u"\u02bc",
    }

    str_to_fix = _replace(str_to_fix, alternative_spaces, " ")
    str_to_fix = _replace(str_to_fix, alternative_dashes, "-")
    str_to_fix = _replace(str_to_fix, alt_double_quotes, "\"")
    str_to_fix = _replace(str_to_fix, alt_single_quotes, "\'")

    return str_to_fix


def find_non_ascii_chars(obj: Any) -> Set[str]:
    found_chars = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            found_chars.update(find_non_ascii_chars(k))
            found_chars.update(find_non_ascii_chars(v))
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            found_chars.update(find_non_ascii_chars(v))
    elif hasattr(obj, "__dict__"):
        found_chars.update(find_non_ascii_chars(obj.__dict__))
    elif isinstance(obj, str):
        for char in obj:
            strange_char = re.sub("[ -~]", "", char)
            if strange_char:
                found_chars.add(strange_char)

    return found_chars


def split_name_str(person_str) -> Tuple[str, str, str, str]:
    name_parts = person_str.split(" ")

    known_roles = ["Präsident", "Vizepräsident"]
    found_role = ""
    for role in known_roles:
        if name_parts[0].startswith(role):
            found_role = role
            name_parts.pop(0)
            break

    # this can be false if in the middle of the name appears one of the
    # following, but I think this shouldn't be the case.
    known_titles = {"Dr.", "h.", "c."}
    found_titles = " ".join([p for p in name_parts if p in known_titles])
    name_parts = [p for p in name_parts if p not in known_titles]

    # remove eventual break ups of the roles for example in "Vizepräsident in"
    name_parts = [p for p in name_parts if not p.islower()]

    return found_role, found_titles, " ".join(name_parts[:-1]), name_parts[-1]


def run_async(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def get_session_id_safe(legislative_period: str, session_no: str) -> str:
    if len(session_no) == 1:
        session_no_safe = f"00{session_no}"
    elif len(session_no) == 2:
        session_no_safe = f"0{session_no}"
    else:
        session_no_safe = session_no
    return f"{legislative_period}{session_no_safe}"


def get_crawled_session(session_id: str) -> dict:
    # todo: testing is needed to access DB from group 1, probably need to specify query better to receive single session
    # db & collection name is still unknown

    crawled_db = database.get_crawler_db()

    if not crawled_db:
        logging.warning("External DB access was not successful. Using test data...")
        time.sleep(4)
        with open("./resources/plenarprotokolle/group_1/19_181_187.json", "r") as read_file:
            session = json.load(read_file)
        return session

    collection_name = "session"
    query = {'_id': session_id}
    session = run_async(crawled_db[collection_name].find_one(query))

    if session:
        logging.info(f"Successful retrieved session '{session_id}' from external DB")
        return session
    return {}


def notify_sentiment_analysis_group(session_list: list):
    # todo: update when group 3 has data
    sentiment_analysis_ip = os.environ.get("SENTIMENT_ANALYSIS_IP")
    url = f"{sentiment_analysis_ip}/update"
    response = requests.post(url, json=session_list)
    if response.status_code in [200, 204]:
        logging.info(f"Successfully notified sentiment analysis about updated sessions")


def get_basic_auth_client(credentials: HTTPBasicCredentials):
    # on dev landscape allow without authentication
    if os.environ.get("LANDSCAPE") == 'dev':
        logging.info("Skipping auth because on dev landscape.")
        return

    client = database.find_one('client', {'_id': credentials.username})
    if not client:
        error.raise_401(f"Incorrect credentials 1 for client '{credentials.username}'")

    try:
        password = os.environ.get(f"{credentials.username.upper()}_PASSWORD")
        if credentials.password != password:
            error.raise_401(f"Incorrect credentials 2 for client '{credentials.username}'")
    except KeyError:
        error.raise_401(f"Incorrect credentials 3 for client '{credentials.username}'")

    return
