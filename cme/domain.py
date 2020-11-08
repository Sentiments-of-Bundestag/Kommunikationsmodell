"""This module contains all our internally used data structures in a central
place"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Set, Tuple, Union

from pydantic import BaseModel


# is domain really needed?
# do we need to typecheck some documents?
# we get list of str from group 1, we have user & faction objects
# we send our own structure to group 2, so we dont need to validate?


class Faction(Enum):
    """Enum representing a Faction in the german bundestag. The values can be
    constructed by name or bundestag opendata faction ids."""

    def __new__(cls, possible_names: List[str]):
        f_id = "F{:03d}".format(len(cls))

        obj = object.__new__(cls)
        obj._value_ = f_id
        obj._possible_names = possible_names

        return obj

    CDU_AND_CSU = (["CDU/CSU", "CDU", "CSU", "Christlich Demokratische Union",
                    "Christlich-Soziale Union", "Union", "Schwarz"])
    SPD = (["SPD", "Sozialdemokratische Partei", "Sozialdemokraten",
            "Sozialdemokrat", "Rot"])
    DIE_LINKE = (["DIE LINKE", "Die Linke", "Linke" "Linkspartei", "Rot"])
    DIE_GRÜNEN = (["BÜNDNIS 90/DIE GRÜNEN", "Bündnis 90/Die Grünen",
                   "Die Grünen", "Bündnis 90", "Grün"])
    AFD = (["AfD", "Alternative für Duetschland", "Blau"])
    FDP = (["FDP", "Freie Demokratische Partei", "Freie Demokraten",
            "Liberale", "Gelb"])
    NONE = (["Fraktionslos"])

    # historical factions
    #GB_AND_BHE = (["GB/BHE", "BHE", "Gesamtdeutscher Block/Bund der Heimatvertriebenen und Entrechteten"])
    #BP = (["BP", "Bayernpartei"])
    #DP = (["DP", "Deutsche Partei"])
    #NDP = (["NDP", "Nationaldemokratische Partei",
    #        "National-Demokratische Partei"])
    #KPD = (["KPD", "Kommunistische Partei"])
    #WAV = (["WAV", "Wirtschaftliche Aufbau-Vereinigung"])
    #DZP = (["DZP", "Deutsche Zentrumspartei"])
    #DRP = (["DRP", "Deutsche Reichs-Partei", "Deutsche Rechtspartei"])
    #DKP = (["DKP", "Deutsche Konservative Partei"])

    @property
    def possible_names(self) -> List[str]:
        """All stored alternative names representing the Enum Value."""
        return self._possible_names.copy()

    @classmethod
    def from_name(cls, name: str) -> "Faction":
        """Utility function to return the first fitting enum value with the
        corresponding name. If the name is not a unique name representative
        in_text should be used to get all possible matches."""

        if name is "":
            return cls.NONE

        for var in cls:
            if name in var._possible_names:
                return var

        raise KeyError()

    @classmethod
    def from_bundestag_od_id(cls, bf_id: str) -> "Faction":
        """Utility function to return the correct Enum Object based on the
        id used by the bundestag opendata xml format. If the given id is not
        valid a KeyError is thrown."""

        mapping = {
            "1": Faction.CDU_AND_CSU,
            "2": Faction.SPD,
            "3": Faction.DIE_LINKE,
            "4": Faction.DIE_GRÜNEN,
            "5": Faction.AFD,
            "6": Faction.FDP,
            "7": Faction.NONE,
        }

        return mapping[bf_id]

    @classmethod
    def in_text(cls, text: str) -> List["Faction"]:
        """Utility function which returns a list of Faction objects which
        are noted through one of there possible_names in the given text."""

        found = set()
        for faction in cls:
            for name in faction._possible_names:
                if name in text:
                    found.add(faction)
                    break

        return list(found)

    @property
    def id(self) -> str:
        return self.value


class SessionMetadata(BaseModel):
    session_no: int
    legislative_period: int
    start: datetime
    end: datetime


mdb_storage = dict()
mdb_name_map = dict()
next_mdb_id = 0


# member of german bundestag
class MDB(BaseModel):
    speaker_id: str
    forename: str
    surname: str
    memberships: List[Tuple[datetime, Optional[datetime], Faction]]
    birthday: Optional[datetime]
    birthplace: Optional[str]
    title: Optional[str]
    job_title: Optional[str]

    @property
    def id(self) -> str:
        return self.speaker_id

    @classmethod
    def give_me_a_better_name(
            cls,
            forename: str,
            surname: str,
            memberships: List[Tuple[datetime, Optional[datetime], Faction]],
            birthday: Optional[datetime] = None,
            birthplace: Optional[str] = None,
            title: Optional[str] = None,
            job_title: Optional[str] = None) -> "MDB":

        mdb_id = mdb_name_map.get((forename, surname))
        if not mdb_id:
            global next_mdb_id
            mdb_id = "MDB{:06d}".format(next_mdb_id)
            next_mdb_id += 1

            mdb = cls(
                speaker_id=mdb_id,
                forename=forename,
                surname=surname,
                memberships=memberships,
                birthday=birthday,
                birthplace=birthplace,
                title=title,
                job_title=job_title)

            mdb_storage[mdb_id] = mdb
            mdb_name_map[(forename, surname)] = mdb_id

        return mdb_storage[mdb_id]

    # todo: we need a persistent mapping somewhere here to safely get MDBs
    #  from the db and return the MDB object based on them or add them to the
    #  db if they where missing.


class InteractionCandidate(BaseModel):
    speaker: MDB
    paragraph: str
    comment: Optional[str]


class Interaction(BaseModel):
    sender: Union[MDB, Faction, str]
    receiver: Union[MDB, Faction, str]
    message: str
    debug: Optional[Dict]

    def dict(self, *args, **kwargs) -> Dict:
        # this overrides the default dict function to clean up fields for the
        # json serialization

        new_dict = BaseModel.dict(self, *args, **kwargs)

        def _to_id(value) -> str:
            if isinstance(value, Faction):
                return value.value
            elif isinstance(value, dict):
                return value["speaker_id"]

            raise RuntimeError("received an unhandled sender or receiver value!")

        new_dict["sender"] = _to_id(new_dict["sender"])
        new_dict["receiver"] = _to_id(new_dict["receiver"])

        return new_dict


class Transcript(BaseModel):
    session_no: int
    legislative_period: int
    start: datetime
    end: datetime
    interactions: List[Interaction]
    factions: Dict[str, Faction]
    speakers: Dict[str, MDB]

    @classmethod
    def from_interactions(
            cls,
            metadata: SessionMetadata,
            interactions: List[Interaction]) \
            -> "Transcript":

        faction_map = dict()
        mdb_map = dict()

        for inter in interactions:
            if isinstance(inter.sender, MDB):
                if inter.sender.speaker_id not in mdb_map:
                    mdb_map[inter.sender.speaker_id] = inter.sender
            elif isinstance(inter.sender, Faction):
                if inter.sender.value not in faction_map:
                    faction_map[inter.sender.value] = inter.sender

            if isinstance(inter.receiver, MDB):
                if inter.receiver.speaker_id not in mdb_map:
                    mdb_map[inter.receiver.speaker_id] = inter.receiver
            elif isinstance(inter.receiver, Faction):
                if inter.receiver.value not in faction_map:
                    faction_map[inter.receiver.value] = inter.receiver

        return cls(
            session_no=metadata.session_no,
            legislative_period=metadata.legislative_period,
            start=metadata.start,
            end=metadata.end,
            interactions=interactions,
            factions=faction_map,
            speakers=mdb_map)

    def dict(self, *args, **kwargs) -> Dict:
        # this overrides the default dict function to clean up fields for the
        # json serialization

        new_dict = BaseModel.dict(self, *args, **kwargs)

        new_dict["factions"] = {k: f.possible_names[0] for k, f in new_dict["factions"].items()}
        for k in new_dict["speakers"].keys():
            del new_dict["speakers"][k]["speaker_id"]

        return new_dict


class CommunicationModel(BaseModel):
    transcripts: List[Transcript]
