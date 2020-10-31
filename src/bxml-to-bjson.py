import copy
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Union, Tuple
import logging
import argparse

from bs4 import BeautifulSoup
from bs4 import element as bs4e

#Normaler Text J, J_1, O
#Tagesordnungspunkt A_TOP, T_Beratung, T_Drs, T_E_Drs, T_E_E_Drs, T_E_fett,
#T_NaS, T_NaS_NaS, T_ZP_NaS, T_ZP_NaS_NaS, T_ZP_NaS_NaS_Strich,
#T_Ueberweisung, T_fett, T_ohne_NaS
#Abstimmungslisten AL_Ja-Nein-Enth, AL_Namen, AL_Partei,
#AL_Vorspann_1, AL_Vorspann_2, AL_Vorspann_3
#Anlagen Anlage_2, Anlage_3
#Redner redner
#Namen N
#Zitat Z


class ParagraphType(Enum):
    SPEAKER_SWITCH = 1
    TEXT = 2
    TOPIC = 3
    VOTING = 4
    CITATION = 5
    ATTACHMENTS = 6


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    for xml_file in args.files:
        with xml_file.open(encoding="utf-8") as f:
            soup = BeautifulSoup(f, "xml")
            sv = soup.sitzungsverlauf

            sb = sv.sitzungsbeginn

            session = parse_session_start(sb)
            session["end"] = sv.sitzungsende.get("sitzung-ende-uhrzeit")
            session["legislative_period"] = int(soup.vorspann.find("wahlperiode").getText())
            session["session_no"] = int(soup.vorspann.find("wahlperiode").getText())

            s_day, s_month, s_year = soup.vorspann.datum["date"].split(".")
            s_s_h, s_s_m = session["start"].split(":")
            s_e_h, s_e_m = session["end"].split(":")

            session["start"] = datetime(int(s_year), int(s_month), int(s_day), int(s_s_h), int(s_s_m)).isoformat()
            session["end"] = datetime(int(s_year), int(s_month), int(s_day), int(s_e_h), int(s_e_m)).isoformat()

            topic_elements = sv.find_all("tagesordnungspunkt")
            topics = parse_session_topics(topic_elements)

            # I'am dropping all other information after this point. So if we
            # need something else it should have been converted and should
            # still exist at this point.

            opener = session["opener"]
            del session["opener"]

            relevant = grab_relevant_elements(opener["paragraphs"])
            for top in topics:
                relevant += grab_relevant_elements(top["paragraphs"])

            session["messages"] = relevant

            session = fix_strange_spaces(session)

            with open(xml_file.with_suffix(".json"), "w", encoding="utf-8") as o:
                json.dump(relevant, o, indent=4, sort_keys=True, ensure_ascii=False)
