import logging
from datetime import datetime, date
from pathlib import Path
from typing import List, Tuple

from bs4 import BeautifulSoup, element as bs4e

from cme.domain import InteractionCandidate, SessionMetadata, MDB, Faction
from cme.utils import cleanup_str, split_name_str, build_datetime


def _safe_get_text(element: bs4e.Tag, child_tag: str, default=""):
    searched_child = element.find(child_tag)
    if searched_child: return cleanup_str(searched_child.getText())
    return default


def _extract_metadata_xml(root_el: bs4e.Tag) -> SessionMetadata:
    head_el = root_el.vorspann.kopfdaten
    sv_el = root_el.sitzungsverlauf

    sn_el = head_el.find("sitzungsnr")
    lp_el = head_el.find("wahlperiode")

    date_str = root_el.get("sitzung-datum")
    session_start = root_el.get("sitzung-start-uhrzeit")
    session_end = root_el.get("sitzung-ende-uhrzeit")

    return SessionMetadata(
        session_no=int(sn_el.getText()),
        legislative_period=int(lp_el.getText()),
        start=build_datetime(date_str, session_start),
        end=build_datetime(date_str, session_end))


def _extract_paragraphs_xml(root_el: bs4e.Tag) -> List[InteractionCandidate]:
    def _extract(
            block_el: bs4e.Tag,
            curr_speaker: MDB = None,
            curr_paragraph: str = None) \
            -> List[InteractionCandidate]:

        pms = list()
        for el in block_el:
            # there are random line breaks in the file which BeautifulSoup
            # makes accessible but we don't need
            if isinstance(el, bs4e.NavigableString):
                continue
            elif el.name == "name":
                # todo: convert this to a dict
                role, title, first_name, last_name = split_name_str(
                    cleanup_str(el.getText().rstrip(":")))
                curr_speaker = {
                    "forename": first_name,
                    "surname": last_name,
                    "memberships": [(datetime.min, None, Faction.NONE)],
                    "title": role}
            elif el.name == "rede":
                pms += _extract(el, curr_speaker, curr_paragraph)
            elif el.name == "p":
                category = el.get("klasse")

                if category == "redner":
                    curr_speaker = {
                        "forename": _safe_get_text(el.redner, "vorname"),
                        "surname": _safe_get_text(el.redner, "nachname"),
                        "memberships": [(datetime.min, None, Faction.from_name(_safe_get_text(el.redner, "fraktion")))],
                        "title": _safe_get_text(el.redner, "rolle_lang")}
                elif category in ["J", "J_1", "O"]:
                    new_para_str = cleanup_str(el.getText())
                    if curr_paragraph is not None:
                        speaker = curr_speaker if isinstance(curr_speaker, MDB) \
                            else MDB.find_in_storage(**curr_speaker)

                        pms.append(InteractionCandidate(
                            speaker=speaker,
                            paragraph=curr_paragraph,
                            comment=None))
                    curr_paragraph = new_para_str
                else:
                    logging.debug("Ignoring unhandled category \"{}\" of tag "
                                  "p.".format(category))
            elif el.name == "kommentar":
                speaker = curr_speaker if isinstance(curr_speaker, MDB) \
                    else MDB.find_in_storage(**curr_speaker)

                pms.append(InteractionCandidate(
                    speaker=speaker,
                    paragraph=curr_paragraph,
                    comment=cleanup_str(el.getText())))
                curr_paragraph = None

        # finish still open curr_paragraph
        if curr_paragraph is not None:
            speaker = curr_speaker if isinstance(curr_speaker, MDB) \
                else MDB.find_in_storage(**curr_speaker)

            pms.append(InteractionCandidate(
                speaker=speaker,
                paragraph=curr_paragraph,
                comment=None))

        return pms

    pms = _extract(root_el.sitzungsverlauf.sitzungsbeginn)

    original_speaker = None

    if pms:
        original_speaker = pms[0].speaker

    for topic_group_el in root_el.sitzungsverlauf.find_all("tagesordnungspunkt"):
        if isinstance(topic_group_el, bs4e.NavigableString):
            continue
        pms += _extract(topic_group_el, original_speaker)

    return pms


def read_transcript_xml_file(
        file: Path) \
        -> Tuple[SessionMetadata, List[InteractionCandidate]]:

    with file.open(mode="rb") as f:
        soup = BeautifulSoup(f, "xml")

        root_el = soup.dbtplenarprotokoll
        metadata = _extract_metadata_xml(root_el)

        candidates = _extract_paragraphs_xml(root_el)

    return metadata, candidates
