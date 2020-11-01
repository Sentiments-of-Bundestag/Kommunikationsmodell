import copy
import json
import re
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Dict, Union, Tuple, List
import logging
import argparse

from bs4 import BeautifulSoup
from bs4 import element as bs4e


class PoliticalFractions(Enum):
    DIE_GRÜNEN = "BÜNDNIS 90/DIE GRÜNEN"
    FDP = "FDP"
    DIE_LINKE = "DIE LINKE"
    AFD = "AfD"
    CDU_AND_CSU = "CDU/CSU"
    SPD = "SPD"

    @classmethod
    def text_contains(cls, text):
        pos_text_reps = {
            PoliticalFractions.DIE_GRÜNEN: ["BÜNDNIS 90/DIE GRÜNEN", "BÜNDNIS 90", "DIE GRÜNEN"],
            PoliticalFractions.FDP: ["FDP"],
            PoliticalFractions.DIE_LINKE: ["DIE LINKE", "LINKE"],
            PoliticalFractions.AFD: ["AfD"],
            PoliticalFractions.CDU_AND_CSU: ["CDU/CSU"],
            PoliticalFractions.SPD: ["SPD"]
        }

        found = list()
        for fraction, reps in pos_text_reps.items():
            for r in reps:
                if r in text:
                    found.append(fraction)
                    break

        return found


class ParagraphType(Enum):
    SPEAKER_SWITCH = auto()
    TEXT = auto()
    TOPIC = auto()
    VOTING = auto()
    CITATION = auto()
    ATTACHMENTS = auto()


def safe_get_text(element: bs4e.Tag, child_tag: str, default=""):
    searched_child = element.find(child_tag)
    if searched_child:
        return searched_child.getText()
    return default


def parse_paragraph(element: bs4e.Tag) -> Tuple[ParagraphType, Union[str, Dict]]:
    category = element["klasse"]

    if category == "N":
        name: str = element.getText()
        if name.endswith(":"):
            name = name[:-1]
        # todo: maybe look into splitting the name -> see speaker dict below
        return ParagraphType.SPEAKER_SWITCH, name
    elif category in ["J_1", "J", "O"]:
        return ParagraphType.TEXT, element.getText()
    elif category == "redner":
        # we have the get this with find as name is an element of bs4
        name_ele: bs4e.Tag = element.redner.find("name")

        speaker = dict()
        speaker["first_name"] = safe_get_text(name_ele, "vorname")
        speaker["last_name"] = safe_get_text(name_ele, "nachname")
        speaker["fraction"] = safe_get_text(name_ele, "fraktion")
        speaker["full_role"] = safe_get_text(name_ele, "rolle_lang")
        speaker["role"] = safe_get_text(name_ele, "rolle_kurz")

        return ParagraphType.SPEAKER_SWITCH, speaker
    elif category in ["A_TOP", "T_Beratung", "T_Drs", "T_E_Drs", "T_E_E_Drs", "T_E_fett", "T_NaS", "T_NaS_NaS", "T_ZP_NaS", "T_ZP_NaS_NaS", "T_ZP_NaS_NaS_Strich", "T_Ueberweisung", "T_fett", "T_ohne_NaS"]:
        return ParagraphType.TOPIC, element.getText()
    elif category in ["AL_Ja-Nein-Enth", "AL_Namen", "AL_Partei", "AL_Vorspann_1", "AL_Vorspann_2", "AL_Vorspann_3"]:
        return ParagraphType.VOTING, element.getText()
    elif category == "Z":
        return ParagraphType.CITATION, element.getText()
    else:
        logging.warning(
            "Received a not supported paragraph category ({})! Handling it as "
            "simple text.".format(category))
        return ParagraphType.TEXT, element.getText()


def parse_paragraph_blocks(parent: bs4e.Tag):
    paragraphs = list()

    curr_speaker = None
    for child in parent.children:
        if not isinstance(child, bs4e.Tag):
            continue  # skip random line breaks

        if child.name == "name":
            curr_speaker = child.getText()
            # todo: do the same name processing as above
        elif child.name == "p":
            p_type, value = parse_paragraph(child)
            if p_type == ParagraphType.SPEAKER_SWITCH:
                curr_speaker = value
            else:
                paragraphs.append({"speaker": curr_speaker, "content": value})
        elif child.name == "kommentar":
            para = paragraphs[-1]
            if "comments" not in para:
                para["comments"] = list()
            para["comments"].append(child.getText())
        elif child.name == "rede":
            paragraphs.append({"content": parse_paragraph_blocks(child)})
        else:
            raise RuntimeError(
                "tag {} is currently not a supported child of "
                "the {} tag!".format(child.name, parent.name))

    return paragraphs


def parse_session_start(element: bs4e.Tag):
    start_dict = dict()
    start_dict["start"] = element.get("sitzung-start-uhrzeit")
    opener = dict()
    start_dict["opener"] = opener
    opener["paragraphs"] = parse_paragraph_blocks(element)

    return start_dict


def parse_session_topics(topic_elements: bs4e.Tag):
    topics = list()
    for single_topic in topic_elements:
        topic_dict = dict()
        topics.append(topic_dict)
        topic_dict["id"] = single_topic["top-id"]
        topic_dict["paragraphs"] = parse_paragraph_blocks(single_topic)

    return topics


def grab_relevant_elements(paragraphs):
    relevant = list()

    for para in paragraphs:
        if "comments" in para:
            assert len(para["comments"]) == 1
            mod_para = copy.deepcopy(para)
            mod_para["comment"] = mod_para["comments"][0]
            del mod_para["comments"]
            relevant.append(mod_para)
        elif isinstance(para["content"], list):
            relevant += grab_relevant_elements(para["content"])

    return relevant


def fix_strange_spaces(value):
    if isinstance(value, dict):
        for k in list(value.keys()):
            value[k] = fix_strange_spaces(value[k])
    if isinstance(value, list):
        for i in range(len(value)):
            value[i] = fix_strange_spaces(value[i])
    if isinstance(value, str):
        value = value.replace(u"\xa0", " ")  # Zs NO - BREAK SPACE
        value = value.replace(u"\u1680", " ")  # Zs OGHAM SPACE MARK
        value = value.replace(u"\u180e", " ")  # Zs MONGOLIAN VOWEL SEPARATOR
        value = value.replace(u"\u2000", " ")  # Zs EN QUAD
        value = value.replace(u"\u2001", " ")  # Zs EM QUAD
        value = value.replace(u"\u2002", " ")  # Zs EN SPACE
        value = value.replace(u"\u2003", " ")  # Zs EM SPACE
        value = value.replace(u"\u2004", " ")  # Zs THREE - PER - EM SPACE
        value = value.replace(u"\u2005", " ")  # Zs FOUR - PER - EM SPACE
        value = value.replace(u"\u2006", " ")  # Zs SIX - PER - EM SPACE
        value = value.replace(u"\u2007", " ")  # Zs FIGURE SPACE
        value = value.replace(u"\u2008", " ")  # Zs PUNCTUATION SPACE
        value = value.replace(u"\u2009", " ")  # Zs THIN SPACE
        value = value.replace(u"\u200a", " ")  # Zs HAIR SPACE
        value = value.replace(u"\u2028", " ")  # Zl LINE SEPARATOR
        value = value.replace(u"\u2029", " ")  # Zp PARAGRAPH SEPARATOR
        value = value.replace(u"\u202f", " ")  # Zs NARROW NO - BREAK SPACE
        value = value.replace(u"\u205f", " ")  # Zs MEDIUM MATHEMATICAL SPACE
        value = value.replace(u"\u3000", " ")  # Zs IDEOGRAPHIC SPACE

    return value


def build_person_dict(person_str):
    # the following lines are a workaround for the somehow not working
    # optional matching group for the Abg. string. If someone finds a way to
    # get this optional matching group working feel free to remove also
    # remove the following lines
    cut_idx = person_str.find("Abg.")
    if cut_idx >= 0:
        cut_idx = person_str.find(" ", cut_idx)
        person_str = person_str[cut_idx:].strip()

    work_str = person_str
    person_parts = list()
    metadata_parts = list()
    while "[" in work_str:
        start_idx = work_str.find("[")
        end_idx = work_str.find("]", start_idx) + 1

        person_parts.append(work_str[:start_idx].strip())
        metadata_parts.append(work_str[start_idx:end_idx].strip().strip("[]"))
        work_str = work_str[end_idx:]

    full_name = " ".join(person_parts)

    # this can be false if in the middle of the name appears one of the
    # following, but I think this shouldn't be the case.
    known_titles = {"Dr.", "h.", "c."}
    name_parts = [
        p for p in full_name.split(" ")
        if p not in known_titles]

    fraction = ""
    for mp in metadata_parts:
        found_fractions = PoliticalFractions.text_contains(mp)
        if found_fractions:
            assert len(found_fractions) == 1
            fraction = found_fractions[0].value
            break

    return {
        "first_name": " ".join(name_parts[:-1]),
        "last_name": name_parts[-1],
        "fraction": fraction,
        "full_role": "",
        "role": ""
    }


def extract_interactions(raw_interactions):
    human_sender_re = re.compile(r"(?:Abg\.\s*)?(?P<person>.+])")
    reformatted_interactions = list()

    def _extract(text_part):
        # todo: this can probably be simplified/ improved by extracting some
        #  generics functions from the following code.

        # converting direct speech separated with a colon
        if ":" in text_part:
            ps, pm = [s.strip() for s in text_part.split(":", 1)]
            pr = None

            # grabbing the special case of a changed receiver during the
            # comment
            if ", an" in ps or ", zur" in ps:
                ps, pr = [s.strip() for s in ps.split(",", 1)]

                pr_match = human_sender_re.search(pr)
                pfr = PoliticalFractions.text_contains(pr)
                if pr_match:
                    pr = pr_match.group("person")
                elif pfr:
                    assert len(pfr) == 1
                    pr = pfr[0]
                else:
                    logging.warning("not handled alternative receiver {}".format(pr))

            # extraction of the sender or senders
            phs = human_sender_re.findall(ps)
            if phs:
                if len(phs) != 1:
                    raise RuntimeError(
                        "Found multiple possible direct speaker ({}) in \"{}\"! "
                        "This is currently not supported".format(phs, text_part))

                if isinstance(pr, str):
                    pr = build_person_dict(pr)
                elif isinstance(pr, PoliticalFractions):
                    pr = pr.value

                return [(
                    build_person_dict(phs[0]),
                    pr,
                    pm)]
            else:
                pfs = PoliticalFractions.text_contains(ps)

                if len(pfs) == 0:
                    logging.warning(
                        "Found no direct sender in \"{}\"! Ignoring the "
                        "message...".format(text_part))

                return [(f.value, None, pm) for f in pfs]
        # converting non verbal messages like laughing
        else:
            keywords = {
                "Beifall", "Zuruf", "Heiterkeit", "Zurufe", "Lachen",
                "Wiederspruch", "Widerspruch"}
            words = text_part.split(" ")

            if len(words) == 0:
                logging.warning(
                    "Found a no direct speech message without a sender "
                    "(\"{}\")! Ignoring it now message...".format(text_part))
                return list()

            last_kw_idx = -1
            for i, w in enumerate(words):
                if w in keywords:
                    last_kw_idx = i

            if last_kw_idx < 0:
                logging.warning(
                    "Found no handled keyword in a non direct speech message "
                    "(\"{}\")! Ignoring it now message...".format(text_part))
                return list()

            relevant_text = " ".join(words[last_kw_idx + 1:])
            potential_senders = re.split(r"(?:und)|(?:sowie)|,", relevant_text)

            found_senders = list()
            for ps in potential_senders:
                phs = human_sender_re.findall(ps)

                if phs:
                    if len(phs) != 1:
                        raise RuntimeError(
                            "Found multiple possible direct speaker ({}) in \"{}\"! "
                            "This is currently not supported".format(phs, text_part))

                    found_senders.append((
                        build_person_dict(phs[0]),
                        None,
                        text_part))
                else:
                    pfs = PoliticalFractions.text_contains(ps)

                    if len(pfs) == 0:
                        logging.warning(
                            "Found no direct sender in \"{}\"! Ignoring the "
                            "message...".format(text_part))

                    found_senders += [(f.value, None, text_part) for f in pfs]

            return found_senders

    def _split_comments(full_text: str, split_char: str = u"\u2013") -> List[str]:
        # todo: this fails in rare cases in which the text contains this char.
        #   maybe there is a smarter way to handle the splitting with respect
        #   to the possibility of the text containing it
        #   example: Beifall bei der SPD sowie bei Abgeordneten der
        #     CDU/CSU – Bettina Stark-Watzinger [FDP]: Jetzt anfängt – nach
        #     einem Jahr Corona?

        # todo: in at least one case a normal - is used instead of \u2013 to
        #  separate the comments

        splitted = [full_text]
        if split_char in full_text:
            splitted = [p.strip() for p in full_text.split(split_char)]
        return splitted

    for curr_inter in raw_interactions:
        full_text = curr_inter["comment"].strip("()")
        text_parts = _split_comments(full_text)

        for part in text_parts:
            result = _extract(part)
            if result:
                for sender, receiver, message in result:
                    if not receiver:
                        receiver = curr_inter["speaker"]

                    if not receiver:
                        logging.warning("Couldn't find a receiver for \"{}\"".format(part))
                        continue

                    reformatted_interactions.append({
                        "debug": {
                            "full_text": full_text,
                            "part": part},
                        "sender": sender,
                        "receiver": receiver,
                        "message": message})
            else:
                logging.warning("Couldn't extract a message from \"{}\". "
                                "dropping it now...".format(part))

    return reformatted_interactions


def fix_sender_and_receivers(session):
    next_f_id = 0
    r_fractions_map = dict()
    next_p_id = 0
    r_person_map = dict()

    def _lookup(obj):
        if isinstance(obj, str):
            if obj in r_fractions_map:
                return True, r_fractions_map[obj]
        elif isinstance(obj, dict):
            hashable_obj = tuple(sorted(obj.items()))
            if hashable_obj in r_person_map:
                return True, r_person_map[hashable_obj]

        return False, None

    def _fix_either(obj):
        nonlocal next_f_id
        nonlocal next_p_id

        already_mapped, found_id = _lookup(obj)
        if not already_mapped:
            if isinstance(obj, str):
                # Vizepräsiden instead of Vizepräsident is used here as there
                # are random spaces after this in the source files
                if obj.startswith("Vizepräsiden") or obj.startswith("Präsident"):
                    found_id = _fix_either(
                        build_person_dict(obj[obj.find(" "):].rstrip(":")))
                else:
                    found_id = "F{}".format(next_f_id)
                    next_f_id += 1
                    r_fractions_map[obj] = found_id
            elif isinstance(obj, dict):
                found_id = "P{}".format(next_p_id)
                next_p_id += 1
                r_person_map[tuple(sorted(obj.items()))] = found_id

        if not found_id:
            logging.warning("received a unhandled {} as a receiver or sender to fix!".format(obj))

        return found_id

    for inter in session["interactions"]:
        inter["sender"] = _fix_either(inter["sender"])
        inter["receiver"] = _fix_either(inter["receiver"])

    def _reverse_dict(dict_obj):
        def _rebuild_dict(potential_dict):
            if isinstance(potential_dict, tuple):
                return {k: v for k, v in potential_dict}
            return potential_dict

        return {v: _rebuild_dict(k) for k, v in dict_obj.items()}

    session["factions"] = _reverse_dict(r_fractions_map)
    session["speakers"] = _reverse_dict(r_person_map)

    for speaker in session["speakers"].values():
        fraction_str = speaker.get("fraction")
        if fraction_str:
            speaker["fraction"] = _fix_either(fraction_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    for xml_file in args.files:
        print("converting {}".format(xml_file.as_posix()))
        with xml_file.open(encoding="utf-8") as f:
            soup = BeautifulSoup(f, "xml")
            sv = soup.sitzungsverlauf

            sb = sv.sitzungsbeginn

            session = parse_session_start(sb)
            session["end"] = sv.sitzungsende.get("sitzung-ende-uhrzeit")
            session["legislative_period"] = int(soup.vorspann.find("wahlperiode").getText())
            session["session_no"] = int(soup.vorspann.find("wahlperiode").getText())

            s_day, s_month, s_year = soup.vorspann.datum["date"].split(".")
            if ":" in session["start"]:
                s_s_h, s_s_m = session["start"].split(":")
            else:
                s_s_h, s_s_m = session["start"].split(".")
            if ":" in session["end"]:
                s_e_h, s_e_m = session["end"].split(":")
            else:
                s_e_h, s_e_m = session["end"].split(".")

            session["start"] = datetime(int(s_year), int(s_month), int(s_day), int(s_s_h), int(s_s_m)).isoformat()
            session["end"] = datetime(int(s_year), int(s_month), int(s_day), int(s_e_h), int(s_e_m)).isoformat()

            topic_elements = sv.find_all("tagesordnungspunkt")
            topics = parse_session_topics(topic_elements)

            # I'm dropping all other information after this point. So if we
            # need something else it should have been converted and should
            # still exist at this point.

            opener = session["opener"]
            del session["opener"]

            print("grabbing relevant elements")
            relevant = grab_relevant_elements(opener["paragraphs"])
            for top in topics:
                relevant += grab_relevant_elements(top["paragraphs"])

            print("fixing strings")
            session["interactions"] = relevant
            session = fix_strange_spaces(session)

            print("extracting interactions")
            session["interactions"] = extract_interactions(session["interactions"])

            fix_sender_and_receivers(session)

            print("writing json")

            with open(xml_file.with_suffix(".json"), "w", encoding="utf-8") as o:
                json.dump({"transcripts": [session]}, o, indent=4, sort_keys=True, ensure_ascii=False)
