import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

from cme.domain import InteractionCandidate, Interaction, MDB, Faction
from cme import utils


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

    # this can be false if in the middle of the name appears one of the
    # following, but I think this shouldn't be the case.
    known_titles = {"Dr.", "h.", "c."}
    name_parts = [
        p for p in full_name.split(" ")
        if p not in known_titles]

    name_parts = [p for p in name_parts if p]

    faction = ""
    for mp in metadata_parts:
        found_factions = Faction.in_text(mp)
        if found_factions:
            assert len(found_factions) == 1
            faction = found_factions[0]
            break

    membership = list()
    if faction:
        membership = [(datetime.min, None, faction)]

    # merging of name parts which are separated with a space between a dash and the two words
    tmp_np = name_parts.copy()
    tmp_np.reverse()
    name_parts.clear()
    while tmp_np:
        part = tmp_np.pop()

        if not tmp_np:
            name_parts.append(part)
            break

        elif part.endswith("-"):
            name_parts.append(part + tmp_np.pop())
        elif tmp_np[0].startswith("-"):
            name_parts.append(part + tmp_np.pop())
        else:
            name_parts.append(part)

    # splitting of names with german noble titles & prefix
    # todo ralph: fix prefix removal q:D
    prefixes = ['von der', 'von und zu', 'von', 'de', 'zu', 'van', 'vom', 'zu']
    for prefix in prefixes:
        if prefix in " ".join(name_parts):
            noble_title_idx = name_parts.index("von")

        if noble_title_idx > 0:
            noble_titles = {"Freiherr", "Baron", "Fürst", "Graf", "Frhr.", "Prinz", "Gräfin", "Prinz zu"}
            if name_parts[noble_title_idx - 1] in noble_titles:
                noble_title_idx -= 1

        forename = " ".join(name_parts[:noble_title_idx])
        surname = " ".join(name_parts[noble_title_idx:])
    else:
        # fallthrough in which case the last word is assumed to be the surname
        forename = " ".join(name_parts[:-1])
        surname = name_parts[-1]

    # detection of malformed extractions
    malformed = not forename
    malformed = malformed or not surname
    extended_keywords = keywords.copy()
    extended_keywords.update(["am", "um", "ne", "wo", "Wo"])  # todo: add more
    for k in extended_keywords:
        malformed = malformed or k in name_parts
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


def _extract_comment_interactions(
        candidates: List[InteractionCandidate],
        add_debug_obj: bool = False) -> List[Interaction]:

    human_sender_re = re.compile(r"(?:Abg\.\s*)?(?P<person>.*\[+.+])")
    reformatted_interactions = list()

    def _extract(text_part: str):
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

    for curr_cand in candidates:
        full_text = curr_cand.comment.strip("()")
        text_parts = _split_comments(full_text)

        for part in text_parts:
            result = _extract(part)
            if result:
                for sender, receiver, message in result:

                    # check for malformed senders or receivers
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

                        continue

                    if not receiver:
                        receiver = curr_cand.speaker

                    if not receiver:
                        logger.warning("Couldn't find a receiver for \"{}\"".format(part))
                        continue

                    inter = {
                        "sender": sender,
                        "receiver": receiver,
                        "message": message}

                    if add_debug_obj:
                        inter["debug"] = {
                            "orig_speaker": curr_cand.speaker,
                            "orig_paragraph": curr_cand.paragraph,
                            "full_comment_text": full_text,
                            "part": part}

                    reformatted_interactions.append(Interaction(**inter))
            else:
                if utils.logging_is_needed(part):
                    logger.warning("Couldn't extract a message from \"{}\". "
                                   "dropping it now...".format(part))

    return reformatted_interactions


def extract_communication_model(
        candidates: List[InteractionCandidate],
        add_debug_objects: bool = False) \
        -> List[Interaction]:

    interactions = _extract_comment_interactions(
        list(filter(lambda i: i.comment is not None, candidates)),
        add_debug_obj=add_debug_objects)

    # todo: handle inner paragraph comments

    return interactions
