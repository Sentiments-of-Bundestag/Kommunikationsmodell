import unittest
from datetime import datetime

from cme.domain import InteractionCandidate, MDB, Faction
from cme.extraction import extract_communication_model


def _build_candidate(comment: str) -> InteractionCandidate:
    return InteractionCandidate(
        speaker=MDB.find_in_storage(
            forename="Likey",
            surname="McUnittest",
            memberships=[(datetime.min, None, Faction.NONE)]),
        paragraph="Unittest",
        comment=comment)


class TestExtraction(unittest.TestCase):

    def test_example_setup(self):
        comment = "(Beifall bei der FDP sowie bei Abgeordneten der CDU/CSU, " \
                  "der SPD und des BÜNDNISSES 90/DIE GRÜNEN – Dr. Eberhardt " \
                  "Alexander Gauland [AfD]: Ha, ha, ha!)"

        cm = extract_communication_model([_build_candidate(comment)])
