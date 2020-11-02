import logging
import re
from enum import Enum
from typing import Dict, List


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


def _extract_comment_interactions(raw_interactions, add_debug_obj: bool = False):
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
                            curr_pr = build_person_dict(curr_pr)
                        elif isinstance(curr_pr, PoliticalFractions):
                            curr_pr = curr_pr.value

                        return [(
                            build_person_dict(phs[0]),
                            curr_pr,
                            pm)]
                else:
                    return [(
                        build_person_dict(phs[0]),
                        None,
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
                        "sender": sender,
                        "receiver": receiver,
                        "message": message})

                    if add_debug_obj:
                        reformatted_interactions[-1]["debug"] = {
                            "orig_speaker": curr_inter["speaker"],
                            "orig_paragraph": curr_inter["paragraph"],
                            "full_comment_text": full_text,
                            "part": part}
            else:
                logging.warning("Couldn't extract a message from \"{}\". "
                                "dropping it now...".format(part))

    return reformatted_interactions


def _fix_sender_and_receivers(interactions):
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

    faction_map = _reverse_dict(r_fractions_map)
    speaker_map = _reverse_dict(r_person_map)

    for speaker in speaker_map.values():
        fraction_str = speaker.get("fraction")
        if fraction_str:
            speaker["fraction"] = _fix_either(fraction_str)

    return fixed_interactions, faction_map, speaker_map


def extract_communication_model(all_interactions: List[Dict]):
    interactions = _extract_comment_interactions(
        list(filter(lambda i: i["comment"] is not None, all_interactions)))

    # todo: handle inner paragraph comments

    interactions, f_map, s_map = _fix_sender_and_receivers(interactions)

    return interactions, f_map, s_map
