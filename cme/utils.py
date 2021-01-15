import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, Tuple, Any, Set, IO, List

import requests
from bson import ObjectId
from fastapi.security import HTTPBasicCredentials
from nameparser import HumanName

from cme import database
from cme.api import error

IGNORED_KEYWORDS = ["Zwischenfrage", "Gegenfrage", "Unruhe", "Glocke der Präsidentin",
                    "Kurzintervention", "nimmt Platz", "Beifall im ganzen Hause", "Unterbrechung", "Nationalhymne",
                    "Heiterkeit", "Nachfrage"]


class SafeJsonEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)

        return json.JSONEncoder.default(self, obj)


def safe_json_dump(obj: Any, fp: IO[str], **kwargs):
    kwargs["cls"] = SafeJsonEncoder
    kwargs["ensure_ascii"] = False
    json.dump(obj, fp, **kwargs)


def safe_json_dumps(obj: Any, **kwargs) -> str:
    kwargs["cls"] = SafeJsonEncoder
    kwargs["ensure_ascii"] = False
    return json.dumps(obj, **kwargs)


def reverse_dict(dict_obj: Dict) -> Dict:
    def _rebuild_dict(potential_dict: Tuple[Tuple]):
        if isinstance(potential_dict, tuple):
            return {k: v for k, v in potential_dict}
        return potential_dict

    return {v: _rebuild_dict(k) for k, v in dict_obj.items()}


def build_datetime(date_str: str or datetime, time_str: str = None, date_order: str = "DMY") -> datetime:
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str

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
    if not str_to_fix:
        return str_to_fix

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


def split_name_str_2(person_str: str) -> Tuple[str, str, str, str]:
    hn = HumanName(person_str)
    
    # todo: fails with 'Dr. h. c. Thomas Sattelberger [FDP]', 'Dr. h. c. Hans Michelbach [CDU/CSU]', 'Dr. Dr. h. c. Karl A. Lamers [CDU/CSU]'
    # todo: 'an Stefan Keuter [AfD]'
    # todo: 'des Abgeordneten Jörg Cezanne [DIE LINKE]'
    # todo:  'der Dr. Silke Launert [CDU/CSU]'
    # todo: '. Michael Grosse-Brömer [CDU/CSU]'

    title = hn.title
    forename = hn.first
    surname = hn.last

    ge_noble_titles = [
        "Baronin", "Baron", "Freiherr", "Frhr.", "Fürstin", "Fürst", "Gräfin", "Graf",
        "Prinzessin", "Prinz"]
    known_prefixes = [
        "von und zu", "von der", "de", "van", "vom", "von", "zu"]

    # grab noble title and add to surname_prefix
    found_prefixes = []
    if hn.middle_list:
        middle_parts = hn.middle_list

        for m_idx in range(len(middle_parts)):
            candidate = middle_parts[m_idx]
            if candidate in ge_noble_titles:
                found_prefixes.append(candidate)
                middle_parts = middle_parts[m_idx + 1:]
                break

        for m_idx in range(len(middle_parts)):
            candidate = middle_parts[m_idx]
            if candidate in known_prefixes:
                found_prefixes.append(candidate)
                break

    for prefix in known_prefixes:
        if surname.startswith(prefix):
            found_prefixes.append(prefix)
            surname = surname.replace(prefix, "").strip()
            break

    surname_prefix = " ".join(found_prefixes)

    return title, forename, surname_prefix, surname


def split_name_str(person_str: str) -> Tuple[str, str, str, str, str]:
    # random special cases
    person_str = person_str.replace("Vizepräsident in", "Vizepräsidentin")

    name_parts = person_str.split(" ")

    known_roles = [
        "Präsident", "Vizepräsident", "Alterspräsident"]

    found_role = ""
    for role in known_roles:
        if name_parts[0].startswith(role):
            found_role = role
            name_parts.pop(0)
            break

    title, forename, surname_prefix, surname = split_name_str_2(
        " ".join(name_parts))

    if not forename:
        logging.error(f"splitted a person string ({person_str}) without a forename!")
    if not surname:
        logging.error(f"splitted a person string ({person_str}) without a surname!")

    return found_role, title, forename, surname_prefix, surname


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
    crawler_db = database.get_crawler_db()

    if not crawler_db:
        logging.warning("External DB access was not successful. Aborting...")
        time.sleep(4)
        return {}

    collection_name = "protokoll"
    # todo: cast check
    query = {'_id': int(session_id)}
    session = crawler_db[collection_name].find_one(query)

    if session:
        logging.info(f"Successful retrieved session '{session_id}' from external DB")
        return session
    return {}


def notify_sentiment_analysis_group(session_list: List[str]):
    sentiment_address = os.environ.get("SENTIMENT_ADDRESS")
    if not sentiment_address:
        logging.error(f"Please provide the env var: 'SENTIMENT_ADDRESS' to notify sentiment group.")
        return

    try:
        response = requests.post(sentiment_address, json={'new_ids': session_list})

        if response.status_code in [200, 204]:
            logging.info(f"Successfully notified sentiment analysis about updated sessions")
        else:
            logging.warning(f"Could not notify sentiment group. Response: '{response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError as error:
        logging.error(f"Could not connect to '{sentiment_address}' for ids: '{session_list}.")
        #logging.error(f"Error: {error}")


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


def logging_is_needed(message: str) -> bool:
    if message == "Beifall" or message == "" or message == "()":
        return False
    if any(keyword in message for keyword in IGNORED_KEYWORDS):
        return False
    return True
