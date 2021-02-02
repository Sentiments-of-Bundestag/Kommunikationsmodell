import unittest

from cme.utils import split_name_str


class TestNameSplitting(unittest.TestCase):

    def test_people_with_default_structure(self):
        candidates = [
            ("Vorname Nachname", "", "", "Vorname", "Nachname")
        ]

        for cand in candidates:
            res = split_name_str(cand[0])
            self.assertTupleEqual(res, cand[1:])

    def test_people_with_role(self):
        candidates = [
            ("Präsident Dr. Manfred Jürgenson von Kuchenhausen", "Präsident", "Dr.", "Manfred", "von Kuchenhausen")
        ]

        for cand in candidates:
            res = split_name_str(cand[0])
            self.assertTupleEqual(res, cand[1:])

    def test_people_with_titles(self):
        candidates = [
            ("Dr. Test Senior", "", "Dr.", "Test", "Senior"),
            ("Dr. h. c. Thomas Sattelberger", "", "Dr. h. c.", "Thomas", "Sattelberger"),
            ("Dr. Dr. h. c. Karl A. Lamers", "", "Dr. Dr. h. c.", "Karl", "Lamers"),
            ("B.Sc. Vorname Nachname", "", "B.Sc.", "Vorname", "Nachname"),
            ("Dr. h. c. Dr. Ing. e. h. Vorname Nachname", "", "Dr. h. c. Dr. Ing. e. h.", "Vorname", "Nachname"),
        ]

        for cand in candidates:
            res = split_name_str(cand[0])
            self.assertTupleEqual(res, cand[1:])

    def test_people_with_noble_titles(self):
        candidates = [
            ("Beatrix von Storch", "", "", "Beatrix", "von Storch"),
            ("Dr. Konstantin von Notz", "", "Dr.", "Konstantin", "von Notz"),
            ("Berengar Elsner von Gronow", "", "", "Berengar", "von Gronow"),
            ("Dr. Daniela De Ridder", "", "Dr.", "Daniela", "De Ridder"),
            ("Christian Frhr. von Stetten", "", "", "Christian", "Frhr. von Stetten"),
            ("Hans-Georg von der Marwitz", "", "", "Hans-Georg", "von der Marwitz"),
            ("Dr. Thomas de Maizière", "", "Dr.", "Thomas", "de Maizière")
        ]

        for cand in candidates:
            res = split_name_str(cand[0])
            self.assertTupleEqual(res, cand[1:])

    def test_people_with_multiple_forenames(self):
        candidates = [
            ("Axel E. Fischer", "", "", "Axel", "Fischer"),
            ("Dr. Johann David Wadephul", "", "Dr.", "Johann", "Wadephul"),
            ("Bettina Margarethe Wiesmann", "", "", "Bettina", "Wiesmann"),
            ("Dr. Ernst Dieter Rossmann", "", "Dr.", "Ernst", "Rossmann"),
            ("Mariana Iris Harder-Kühnel", "", "", "Mariana", "Harder-Kühnel"),
            ("Tobias Matthias Peterka", "", "", "Tobias", "Peterka"),
            ("Eberhardt Alexander Gauland", "", "", "Eberhardt", "Gauland")
        ]

        for cand in candidates:
            res = split_name_str(cand[0])
            self.assertTupleEqual(res, cand[1:])
