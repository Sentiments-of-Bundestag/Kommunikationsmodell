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

    def test_extract_sample1(self):
        comment = "(Beifall bei der FDP sowie bei Abgeordneten der CDU/CSU, der SPD und des BÜNDNISSES 90/DIE GRÜNEN – Dr. Eberhardt Alexander Gauland [AfD]: Ha, ha, ha!)"

        cm = extract_communication_model([_build_candidate(comment)])
        interaction_0 = cm[0]
        interaction_1 = cm[1]
        interaction_2 = cm[2]
        interaction_3 = cm[3]
        interaction_4 = cm[4]
        self.assertEqual(interaction_0.sender, Faction.FDP)
        self.assertEqual(interaction_0.message, 'Beifall bei der FDP sowie bei Abgeordneten der CDU/CSU, der SPD und '
                                                'des BÜNDNISSES 90/DIE GRÜNEN')
        self.assertEqual(interaction_1.sender, Faction.CDU_AND_CSU)
        self.assertEqual(interaction_1.message, 'Beifall bei der FDP sowie bei Abgeordneten der CDU/CSU, der SPD und '
                                                'des BÜNDNISSES 90/DIE GRÜNEN')
        self.assertEqual(interaction_2.sender, Faction.SPD)
        self.assertEqual(interaction_2.message, 'Beifall bei der FDP sowie bei Abgeordneten der CDU/CSU, der SPD und '
                                                'des BÜNDNISSES 90/DIE GRÜNEN')
        self.assertEqual(interaction_3.sender, Faction.DIE_GRÜNEN)
        self.assertEqual(interaction_3.message, 'Beifall bei der FDP sowie bei Abgeordneten der CDU/CSU, der SPD und '
                                                'des BÜNDNISSES 90/DIE GRÜNEN')
        self.assertEqual(interaction_4.sender, MDB.find_in_storage(forename="Eberhardt Alexander", surname="Gauland", memberships=[(datetime.min, None, Faction.AFD)]))
        self.assertEqual(interaction_4.message, 'Ha, ha, ha!')

    def test_extract_sample2(self):
        comment = "(Beifall bei der CDU/CSU, der SPD, der FDP, der LINKEN und dem BÜNDNIS 90/DIE GRÜNEN – Zuruf des Abg. Armin-Paulus Hampel [AfD])"

        cm = extract_communication_model([_build_candidate(comment)])
        interaction_0 = cm[0]
        interaction_1 = cm[1]
        interaction_2 = cm[2]
        interaction_3 = cm[3]
        interaction_4 = cm[4]
        interaction_5 = cm[5]
        self.assertEqual(interaction_0.sender, Faction.CDU_AND_CSU)
        self.assertEqual(interaction_0.message, 'Beifall bei der CDU/CSU, der SPD, der FDP, der LINKEN und dem BÜNDNIS 90/DIE GRÜNEN')
        self.assertEqual(interaction_1.sender, Faction.SPD)
        self.assertEqual(interaction_1.message, 'Beifall bei der CDU/CSU, der SPD, der FDP, der LINKEN und dem BÜNDNIS 90/DIE GRÜNEN')
        self.assertEqual(interaction_2.sender, Faction.FDP)
        self.assertEqual(interaction_2.message, 'Beifall bei der CDU/CSU, der SPD, der FDP, der LINKEN und dem BÜNDNIS 90/DIE GRÜNEN')
        self.assertEqual(interaction_3.sender, Faction.DIE_LINKE)
        self.assertEqual(interaction_3.message, 'Beifall bei der CDU/CSU, der SPD, der FDP, der LINKEN und dem BÜNDNIS 90/DIE GRÜNEN')
        self.assertEqual(interaction_4.sender, Faction.DIE_GRÜNEN)
        self.assertEqual(interaction_4.message, 'Beifall bei der CDU/CSU, der SPD, der FDP, der LINKEN und dem BÜNDNIS 90/DIE GRÜNEN')
        self.assertEqual(interaction_5.sender, MDB.find_in_storage(forename="Armin-Paulus", surname="Hampel", memberships=[(datetime.min, None, Faction.AFD)]))
        self.assertEqual(interaction_5.message, 'Zuruf des Abg. Armin-Paulus Hampel [AfD]')

    def test_extract_sample3(self):
        comment3 = "(Carsten Schneider [Erfurt] [SPD]: Was für ein Blödsinn! – Zuruf vom BÜNDNIS90/DIE GRÜNEN: Vielleicht mal lesen! Lesen bildet!)"

        cm3 = extract_communication_model([_build_candidate(comment3)])
        interaction_0 = cm3[0]
        interaction_1 = cm3[1]

        self.assertEqual(interaction_0.sender, MDB.find_in_storage(forename="Carsten", surname="Schneider", memberships=[(datetime.min, None, Faction.SPD)]))
        self.assertEqual(interaction_0.message, 'Was für ein Blödsinn!')
        self.assertEqual(interaction_1.sender, Faction.DIE_GRÜNEN)
        self.assertEqual(interaction_1.message, 'Zuruf vom BÜNDNIS90/DIE GRÜNEN: Vielleicht mal lesen! Lesen bildet!')


    def test_extract_funny_sample1(self):
        comment = "(Heiterkeit und Beifall bei Abgeordneten der CDU/CSU, der SPD und der LINKEN – Lachen bei der AfD)"

        cm = extract_communication_model([_build_candidate(comment)])
        interaction_0 = cm[0]
        interaction_1 = cm[1]
        interaction_2 = cm[2]
        interaction_3 = cm[3]

        self.assertEqual(interaction_0.sender, Faction.CDU_AND_CSU)
        self.assertEqual(interaction_0.message, 'Heiterkeit und Beifall bei Abgeordneten der CDU/CSU, der SPD und der LINKEN')
        self.assertEqual(interaction_1.sender, Faction.SPD)
        self.assertEqual(interaction_1.message, 'Heiterkeit und Beifall bei Abgeordneten der CDU/CSU, der SPD und der LINKEN')
        self.assertEqual(interaction_2.sender, Faction.DIE_LINKE)
        self.assertEqual(interaction_2.message, 'Heiterkeit und Beifall bei Abgeordneten der CDU/CSU, der SPD und der LINKEN')
        self.assertEqual(interaction_3.sender, Faction.AFD)
        self.assertEqual(interaction_3.message, 'Lachen bei der AfD')

    def test_extract_funny_sample2(self):
        comment = "(Beifall bei der SPD sowie bei Abgeordneten der LINKEN – Matthias W. Birkwald [DIE LINKE]: Ich mich auch!)"

        cm = extract_communication_model([_build_candidate(comment)])
        interaction_0 = cm[0]
        interaction_1 = cm[1]
        interaction_2 = cm[2]

        self.assertEqual(interaction_0.sender, Faction.SPD)
        self.assertEqual(interaction_0.message, 'Beifall bei der SPD sowie bei Abgeordneten der LINKEN')
        self.assertEqual(interaction_1.sender, Faction.DIE_LINKE)
        self.assertEqual(interaction_1.message, 'Beifall bei der SPD sowie bei Abgeordneten der LINKEN')
        self.assertEqual(interaction_2.sender, MDB.find_in_storage(forename="Matthias W.", surname="Birkwald", memberships=[(datetime.min, None, Faction.DIE_LINKE)]))
        self.assertEqual(interaction_2.message, 'Ich mich auch!')

    def test_extract_funny_sample_3(self):
        comment = "(Heiterkeit und Beifall bei der CDU/CSU sowie des Abg. Jens Beeck [FDP])"

        cm = extract_communication_model([_build_candidate(comment)])
        interaction_0 = cm[0]
        interaction_1 = cm[1]

        self.assertEqual(interaction_0.sender, Faction.CDU_AND_CSU)
        self.assertEqual(interaction_0.message, 'Heiterkeit und Beifall bei der CDU/CSU sowie des Abg. Jens Beeck [FDP]')
        self.assertEqual(interaction_1.sender, MDB.find_in_storage(forename="Jens", surname="Beeck", memberships=[(datetime.min, None, Faction.FDP)]))
        self.assertEqual(interaction_1.message, 'Heiterkeit und Beifall bei der CDU/CSU sowie des Abg. Jens Beeck [FDP]')

    def test_extract_funny_sample_4(self):
        comment = "(Heiterkeit des Abg. Manfred Grund [CDU/CSU])"

        cm = extract_communication_model([_build_candidate(comment)])
        interaction_0 = cm[0]

        self.assertEqual(interaction_0.sender, MDB.find_in_storage(forename="Manfred", surname="Grund", memberships=[(datetime.min, None, Faction.CDU_AND_CSU)]))
        self.assertEqual(interaction_0.message, 'Heiterkeit des Abg. Manfred Grund [CDU/CSU]')

