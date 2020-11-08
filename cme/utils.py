from datetime import datetime
from typing import Dict, Tuple, List
import asyncio


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
    str_to_fix = str_to_fix.replace(u"\xa0", " ")  # Zs NO - BREAK SPACE
    str_to_fix = str_to_fix.replace(u"\u1680", " ")  # Zs OGHAM SPACE MARK
    str_to_fix = str_to_fix.replace(u"\u180e", " ")  # Zs MONGOLIAN VOWEL SEPARATOR
    str_to_fix = str_to_fix.replace(u"\u2000", " ")  # Zs EN QUAD
    str_to_fix = str_to_fix.replace(u"\u2001", " ")  # Zs EM QUAD
    str_to_fix = str_to_fix.replace(u"\u2002", " ")  # Zs EN SPACE
    str_to_fix = str_to_fix.replace(u"\u2003", " ")  # Zs EM SPACE
    str_to_fix = str_to_fix.replace(u"\u2004", " ")  # Zs THREE - PER - EM SPACE
    str_to_fix = str_to_fix.replace(u"\u2005", " ")  # Zs FOUR - PER - EM SPACE
    str_to_fix = str_to_fix.replace(u"\u2006", " ")  # Zs SIX - PER - EM SPACE
    str_to_fix = str_to_fix.replace(u"\u2007", " ")  # Zs FIGURE SPACE
    str_to_fix = str_to_fix.replace(u"\u2008", " ")  # Zs PUNCTUATION SPACE
    str_to_fix = str_to_fix.replace(u"\u2009", " ")  # Zs THIN SPACE
    str_to_fix = str_to_fix.replace(u"\u200a", " ")  # Zs HAIR SPACE
    str_to_fix = str_to_fix.replace(u"\u2028", " ")  # Zl LINE SEPARATOR
    str_to_fix = str_to_fix.replace(u"\u2029", " ")  # Zp PARAGRAPH SEPARATOR
    str_to_fix = str_to_fix.replace(u"\u202f", " ")  # Zs NARROW NO - BREAK SPACE
    str_to_fix = str_to_fix.replace(u"\u205f", " ")  # Zs MEDIUM MATHEMATICAL SPACE
    str_to_fix = str_to_fix.replace(u"\u3000", " ")  # Zs IDEOGRAPHIC SPACE

    return str_to_fix


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
    # access to different mongoDB
    print("INFO: getting session from external MongoDB (not yet implemented)")
    # todo create dummy file reader
    return {}



