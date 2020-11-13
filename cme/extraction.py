import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple

from cme.domain import InteractionCandidate, Interaction, MDB, Faction


def _build_mdb(person_str):
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

    return MDB.find_in_storage(
        forename=" ".join(name_parts[:-1]),
        surname=name_parts[-1],
        memberships=membership)


def _extract_comment_interactions(
        candidates: List[InteractionCandidate],
        add_debug_obj: bool = False) -> List[Interaction]:

    human_sender_re = re.compile(r"(?:Abg\.\s*)?(?P<person>.+])")
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
                    logging.warning("not handled alternative receiver {}".format(pr))

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
                            curr_pr = _build_mdb(curr_pr)
                        elif isinstance(curr_pr, Faction):
                            curr_pr = curr_pr

                        return [(
                            _build_mdb(phs[0]),
                            curr_pr,
                            pm)]
                else:
                    return [(
                        _build_mdb(phs[0]),
                        None,
                        pm)]
            else:
                pfs = Faction.in_text(ps)

                if len(pfs) == 0:
                    logging.warning(
                        "Found no direct sender in \"{}\"! Ignoring the "
                        "message...".format(text_part))

                return [(f, None, pm) for f in pfs]
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
                        _build_mdb(phs[0]),
                        None,
                        text_part))
                else:
                    pfs = Faction.in_text(ps)

                    if len(pfs) == 0:
                        logging.warning(
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
                    if not receiver:
                        receiver = curr_cand.speaker

                    if not receiver:
                        logging.warning("Couldn't find a receiver for \"{}\"".format(part))
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
                logging.warning("Couldn't extract a message from \"{}\". "
                                "dropping it now...".format(part))

    return reformatted_interactions


def _fix_sender_and_receivers(interactions):
    next_f_id = 0
    r_factions_map = dict()
    next_p_id = 0
    r_person_map = dict()

    # todo: dont create id's, use id's from faction and MDB collection

    def _lookup(obj):
        if isinstance(obj, str):
            if obj in r_factions_map:
                return True, r_factions_map[obj]
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
                        _build_mdb(obj[obj.find(" "):].rstrip(":")))
                else:
                    found_id = "F{}".format(next_f_id)
                    next_f_id += 1
                    r_factions_map[obj] = found_id
            elif isinstance(obj, dict):
                found_id = "P{}".format(next_p_id)
                next_p_id += 1
                r_person_map[tuple(sorted(obj.items()))] = found_id

        if not found_id:
            logging.warning("received a unhandled {} as a receiver or sender to fix!".format(obj))

        return found_id

    fixed_interactions = list()

    for inter in interactions:
        fixed_interactions.append(inter.copy())
        fixed_interactions[-1]["sender"] = _fix_either(inter["sender"])
        fixed_interactions[-1]["receiver"] = _fix_either(inter["receiver"])

    def _reverse_dict(dict_obj):
        def _rebuild_dict(potential_dict):
            if isinstance(potential_dict, tuple):
                return {k: v for k, v in potential_dict}
            return potential_dict

        return {v: _rebuild_dict(k) for k, v in dict_obj.items()}

    faction_map = _reverse_dict(r_factions_map)
    speaker_map = _reverse_dict(r_person_map)

    for speaker in speaker_map.values():
        faction_str = speaker.get("faction")
        if faction_str:
            speaker["faction"] = _fix_either(faction_str)

    return fixed_interactions, faction_map, speaker_map


def extract_communication_model(
        candidates: List[InteractionCandidate],
        add_debug_objects: bool = False) \
        -> List[Interaction]:

    interactions = _extract_comment_interactions(
        list(filter(lambda i: i.comment is not None, candidates)),
        add_debug_obj=add_debug_objects)

    # todo: handle inner paragraph comments

    return interactions
