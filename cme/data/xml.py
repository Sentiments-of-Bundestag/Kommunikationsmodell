import logging
from collections import namedtuple
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup, element as bs4e

from cme.utils import build_isoformat_time_str, cleanup_str, split_name_str

TranscriptMetadata = namedtuple(
    "TranscriptMetadata",
    ["session_no", "legislative_period", "start", "end"])

TopicParagraph = namedtuple(
    "TopicParagraph",
    ["speaker", "paragraph", "comment"])


def _safe_get_text(element: bs4e.Tag, child_tag: str, default=""):
    searched_child = element.find(child_tag)
    if searched_child: return cleanup_str(searched_child.getText())
    return default


def _extract_metadata_xml(root_el: bs4e.Tag) -> TranscriptMetadata:
    head_el = root_el.vorspann.kopfdaten
    sv_el = root_el.sitzungsverlauf

    sn_el = head_el.find("sitzungsnr")
    lp_el = head_el.find("wahlperiode")

    date_str = root_el.get("sitzung-datum")
    session_start = root_el.get("sitzung-start-uhrzeit")
    session_end = root_el.get("sitzung-ende-uhrzeit")

    return TranscriptMetadata(
        int(sn_el.getText()),
        int(lp_el.getText()),
        build_isoformat_time_str(date_str, session_start),
        build_isoformat_time_str(date_str, session_end))


def _extract_paragraphs_xml(root_el: bs4e.Tag) -> List[TopicParagraph]:
    def _extract(
            block_el: bs4e.Tag,
            curr_speaker=None,
            curr_paragraph=None) \
            -> List[TopicParagraph]:

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
                    "first_name": first_name,
                    "last_name": last_name,
                    "fraction": "",
                    "full_role": role,
                    "role": role}
            elif el.name == "rede":
                pms += _extract(el, curr_speaker, curr_paragraph)
            elif el.name == "p":
                category = el.get("klasse")

                if category == "redner":
                    curr_speaker = {
                        "first_name": _safe_get_text(el.redner, "vorname"),
                        "last_name": _safe_get_text(el.redner, "nachname"),
                        "fraction": _safe_get_text(el.redner, "fraktion"),
                        "full_role": _safe_get_text(el.redner, "rolle_lang"),
                        "role": _safe_get_text(el.redner, "rolle_kurz")}
                elif category in ["J", "J_1", "O"]:
                    new_para_str = cleanup_str(el.getText())
                    if curr_paragraph is not None:
                        pms.append(TopicParagraph(
                            curr_speaker,
                            curr_paragraph,
                            None))
                    curr_paragraph = new_para_str
                else:
                    logging.debug("Ignoring unhandled category \"{}\" of tag "
                                  "p.".format(category))
            elif el.name == "kommentar":
                pms.append(TopicParagraph(
                    curr_speaker,
                    curr_paragraph,
                    cleanup_str(el.getText())))
                curr_paragraph = None

        # finish still open curr_paragraph
        if curr_paragraph is not None:
            pms.append(TopicParagraph(
                curr_speaker,
                curr_paragraph,
                None))

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


def read_xml_transcript(xml_file: Path):
    with xml_file.open(mode="rb") as f:
        soup = BeautifulSoup(f, "xml")

        transcript = dict()
        
        root_el = soup.dbtplenarprotokoll

        metadata = _extract_metadata_xml(root_el)
        transcript["session_no"] = metadata.session_no
        transcript["legislative_period"] = metadata.legislative_period
        transcript["start"] = metadata.start
        transcript["end"] = metadata.end

        paragraphs = list()
        transcript["interactions"] = paragraphs
        for para in _extract_paragraphs_xml(root_el):
            paragraphs.append({
                "speaker": para.speaker,
                "paragraph": para.paragraph,
                "comment": para.comment})

        return transcript
