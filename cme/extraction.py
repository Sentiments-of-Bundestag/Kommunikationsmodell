import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List

from cme import utils, database
from cme.domain import InteractionCandidate, Interaction, MDB, Faction
from cme.utils import split_name_str

logger = logging.getLogger("cme.extraction")

keywords = {
    "Beifall", "Zuruf", "Heiterkeit", "Zurufe", "Lachen",
    "Wiederspruch", "Widerspruch", "Gegenrufe", "Buhrufe", "Pfiffe", "Gegenruf"}


@dataclass
class MalformedMDB:
    person_str: str
    forename: str
    surname: str
    memberships: List


def _build_mdb(person_str, add_debug_obj):
    # the following lines are a workaround for the somehow not working
    # optional matching group for the Abg. string. If someone finds a way to
    # get this optional matching group working feel free to remove also
    # remove the following lines
    cut_idx = person_str.find("Abg.")
    if cut_idx >= 0:
        cut_idx = person_str.find(" ", cut_idx)
        person_str = person_str[cut_idx:].strip()

    person_str = person_str.replace("(", "[")
    person_str = person_str.replace(")", "]")

    num_opening_brackets = person_str.count("[")
    num_closing_brackets = person_str.count("]")

    if num_opening_brackets != num_closing_brackets:
        logger.warning(
            "the received person_str \"{}\" contains not the same amount of "
            "opening brackets as closing brackets. this might become a "
            "problem shortly after this...".format(person_str))

    if num_opening_brackets > num_closing_brackets:
        person_str = person_str.lstrip("[")

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

    faction = ""
    for mp in metadata_parts:
        found_factions = Faction.in_text(mp)
        if found_factions:
            if len(found_factions) != 1:
                logger.info(f"Found factions != 1: {found_factions}")
            assert len(found_factions) == 1
            faction = found_factions[0]
            break

    membership = list()
    if faction:
        membership = [(datetime.min, None, faction)]

    full_name = full_name.replace("- ", "-")
    full_name = full_name.replace(" -", "-")

    role, title, forename, surname_prefix, surname = split_name_str(full_name)

    # detection of malformed extractions
    malformed = not forename
    malformed = malformed or not surname
    extended_keywords = keywords.copy()
    extended_keywords.update(["am", "um", "ne", "wo", "Wo"])  # todo: add more
    for k in extended_keywords:
        malformed = malformed or k in full_name.split(" ")
        if malformed:
            break

    if malformed:
        return MalformedMDB(
            person_str,
            forename,
            surname,
            membership)

    debug_info = None
    if add_debug_obj:
        debug_info = {
            "constructed_from_text": True,
            "creation_person_str": person_str
        }

    return MDB.find_and_add_in_storage(
        forename=forename,
        surname=surname,
        memberships=membership,
        debug_info=debug_info)


human_sender_re = re.compile(r"(?:Abg\.\s*)?(?P<person>.*\[+.+])")


def extract_comment(text_part: str, add_debug_obj: bool = False):
    # converting direct speech separated with a colon
    if ":" in text_part:
        ps, pm = [s.strip() for s in text_part.split(":", 1)]
        pr = None

        # grabbing the special case of a changed receiver during the
        # comment
        if ", an" in ps or ", zur" in ps:
            ps, pr = [s.strip() for s in ps.split(",", 1)]

            pr_match = human_sender_re.search(pr)
            pfr = Faction.in_text(pr)
            if pr_match:
                pr = [pr_match.group("person")]
            elif pfr:
                pr = pfr
            else:
                logger.warning("not handled alternative receiver \"{}\"".format(pr))
                pr = None

        # extraction of the sender or senders
        phs = human_sender_re.findall(ps)
        if phs:
            if len(phs) != 1:
                raise RuntimeError(
                    "Found multiple possible direct speaker ({}) in \"{}\"! "
                    "This is currently not supported".format(phs, text_part))

            if pr:
                for curr_pr in pr:
                    if isinstance(curr_pr, str):
                        curr_pr = _build_mdb(curr_pr, add_debug_obj)
                    elif isinstance(curr_pr, Faction):
                        curr_pr = curr_pr

                    return [(
                        _build_mdb(phs[0], add_debug_obj),
                        curr_pr,
                        pm)]
            else:
                return [(
                    _build_mdb(phs[0], add_debug_obj),
                    None,
                    pm)]
        else:
            pfs = Faction.in_text(ps)

            if len(pfs) == 0 and utils.logging_is_needed(text_part):
                logger.warning(
                    "Found no direct sender in \"{}\"! Ignoring the "
                    "message...".format(text_part))

            return [(f, None, pm) for f in pfs]
    # converting non verbal messages like laughing
    else:
        words = text_part.split(" ")

        if len(words) == 0:
            logger.warning(
                "Found a no direct speech message without a sender "
                "(\"{}\")! Ignoring it now message...".format(text_part))
            return list()

        last_kw_idx = -1
        for i, w in enumerate(words):
            if w in keywords:
                last_kw_idx = i

        if last_kw_idx < 0:
            if utils.logging_is_needed(text_part):
                logger.warning(
                    "Found no handled keyword in a non direct speech message "
                    "(\"{}\")! Ignoring it now message...".format(text_part))
            return list()

        relevant_text = " ".join(words[last_kw_idx + 1:])
        potential_senders = re.split(r"(?:\sund\s)|(?:\ssowie\s)|(?:,\s)", relevant_text)

        found_senders = list()
        for ps in potential_senders:
            phs = human_sender_re.findall(ps)

            if phs:
                if len(phs) != 1:
                    raise RuntimeError(
                        "Found multiple possible direct speaker ({}) in \"{}\"! "
                        "This is currently not supported".format(phs, text_part))

                found_senders.append((
                    _build_mdb(phs[0], add_debug_obj),
                    None,
                    text_part))

            else:
                pfs = Faction.in_text(ps)

                if len(pfs) == 0 and utils.logging_is_needed(text_part):
                    logger.warning(
                        "Found no direct sender in \"{}\"! Ignoring the "
                        "message...".format(text_part))

                found_senders += [(f, None, text_part) for f in pfs]

        return found_senders


def split_comments(full_text: str, split_char: str = u"\u2013") -> List[str]:
    splitted = [full_text]
    if split_char in full_text:
        splitted = [p.strip() for p in full_text.split(split_char)]
    return splitted


def reformat_interaction(sender, receiver, message, from_paragraph: bool = True):
    sender_malformed = isinstance(sender, MalformedMDB)
    receiver_malformed = isinstance(receiver, MalformedMDB)
    if sender_malformed or receiver_malformed:
        if sender_malformed and receiver_malformed:
            logger.error(
                f"Found message \"{message}\" with a broken "
                f"sender \"{sender}\" and receiver "
                f"\"{receiver}\". skipping it...")
        if sender_malformed:
            logger.error(
                f"Found message \"{message}\" with a broken "
                f"sender \"{sender}\". skipping it...")
        else:
            logger.error(
                f"Found message \"{message}\" with a broken "
                f"receiver \"{receiver}\". skipping it...")

        return None

    if not receiver:
        logger.warning("Couldn't find a receiver for \"{}\"".format(message))
        return None

    inter = {
        "sender": sender,
        "receiver": receiver,
        "message": message,
        "from_paragraph": from_paragraph}

    return Interaction(**inter)


def retrieve_paragraph_keymap(add_debug_obj: bool = False):
    # fetch person list from mdb database
    person_keymap = {}
    mdb_list = MDB.find_known_mdbs()
    if len(mdb_list) > 0:
        for mdb in mdb_list:
            keyword = mdb['surname']
            # TODO disambiguation improvement
            # for now, we opt to look for
            # mdb references only by their surname, as we have no method
            # to contextualize role- or forename references enough to tell
            # who's been adressed. Even in this solution, we discard any names
            # that appear multiple times in our database, as we again have no
            # system in place to figure out which entity is meant.
            # TODO fix triple occurence
            if keyword not in person_keymap.keys():
                person_keymap[keyword] = keyword
    for k in person_keymap.keys():
        people = database.find_many("mdb", {"surname": k})
        if not len(people) > 1:
            person_keymap[k] = MDB(**people[0])

    return person_keymap

valid_prepositions = ['Herr', 'Hr.', 'Frau', 'Fr.', 'Dr.', 'Doktor', 'Kollege', 'Kollegin']


def extract_paragraph(text_part: str, paragraph_keymap, add_debug_obj: bool = False):
    text_tokens = text_part.split(" ")

    receivers = []
    paragraph_keywords = paragraph_keymap.keys()

    for index, token in enumerate(text_tokens):
        if token in paragraph_keywords:
            preceding_index = index - 1
            if preceding_index >= 0:
                preceding_token = text_tokens[preceding_index]
                if preceding_token in valid_prepositions:
                    receiver = paragraph_keymap[token]
                    if isinstance(receiver, MDB):
                        receivers.append(receiver)

    receiver_factions = Faction.in_text(text_part)

    receivers.extend(receiver_factions)

    return receivers


def _extract_all_interactions(
        candidates: List[InteractionCandidate],
        add_debug_obj: bool = False) -> List[Interaction]:
    reformatted_interactions = list()
    paragraph_keymap = retrieve_paragraph_keymap()

    for candidate in candidates:
        if candidate.comment is not None:
            # TODO extract paragraph as well
            # extract paragraph interaction
            paragraph_text = candidate.paragraph
            receivers = extract_paragraph(paragraph_text, paragraph_keymap, add_debug_obj)
            if len(receivers) > 0:
                for receiver in receivers:
                    reformatted_interaction = reformat_interaction(candidate.speaker, receiver, paragraph_text, True)
                    if reformatted_interaction:
                        reformatted_interactions.append(reformatted_interaction)
            else:
                logger.warning(
                    f"Couldn't extract a message receiver from paragraph \"{paragraph_text}\", dropping it now...")

            # extract comment interaction
            full_text = candidate.comment.strip("()")
            comment_parts = split_comments(full_text)
            for comment_part in comment_parts:
                extracted_senders = extract_comment(comment_part, add_debug_obj)
                for sender, receiver, message in extracted_senders:
                    if receiver:
                        reformatted_interaction = reformat_interaction(sender, receiver, message, False)
                    else:
                        reformatted_interaction = reformat_interaction(sender, candidate.speaker, message, False)
                    if reformatted_interaction:
                        if add_debug_obj:
                            reformatted_interaction["debug"] = {
                                "orig_speaker": candidate.speaker,
                                "orig_paragraph": candidate.paragraph,
                                "full_comment_text": full_text,
                                "part": comment_part}

                        reformatted_interactions.append(reformatted_interaction)

        else:
            # extract paragraph interaction
            paragraph_text = candidate.paragraph
            receivers = extract_paragraph(paragraph_text, paragraph_keymap, add_debug_obj)
            if len(receivers) > 0:
                for receiver in receivers:
                    reformatted_interaction = reformat_interaction(candidate.speaker, receiver, paragraph_text, True)
                    if reformatted_interaction:
                        reformatted_interactions.append(reformatted_interaction)
            else:
                logger.warning(
                    f"Couldn't extract a message receiver from paragraph \"{paragraph_text}\", dropping it now...")

    return reformatted_interactions


def extract_communication_model(
        candidates: List[InteractionCandidate],
        add_debug_objects: bool = False) \
        -> List[Interaction]:

    # todo: handle inner paragraph comments
    # extract all interactions
    interactions = _extract_all_interactions(list(candidates), add_debug_obj=add_debug_objects)

    return interactions
