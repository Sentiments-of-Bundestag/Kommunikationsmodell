import unittest
import logging
import re
from cme.extraction import _extract_comment_interactions
from cme.extraction import _build_mdb
from cme.domain import InteractionCandidate, MDB, Faction
from datetime import datetime


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

test_comments = ["Beifall von der CSU"]
InteractionCandidate(
    speaker=MDB(forename="Foo", surname="Bar"),
    paragraph="weqew",
    comment="eqwe")

class ExtractionTest(unittest.TestCase):

    def testSimpleBeifall(self):
        test1_senders = _extract(test_comments[0])
        self.assertEqual(test1_senders, ["CSU"])


if __name__ == '__main__':
    unittest.main()
