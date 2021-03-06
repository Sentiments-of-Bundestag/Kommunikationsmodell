"""This module contains all our internally used data structures in a central
place"""
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Tuple, Union

from pydantic import BaseModel

from cme import database

logger = logging.getLogger("cme.domain")


class Faction(Enum):
    """Enum representing a Faction in the german bundestag. The values can be
    constructed by name or bundestag opendata faction ids."""

    def __new__(cls, possible_names: List[str] = None):
        """Builds a new Faction enum value with an automatic value field. If
        possible_names is None a text search is no longer possible and is what
        you want if the faction is considered as legacy."""

        f_id = "F{:03d}".format(len(cls))

        obj = object.__new__(cls)
        obj._value_ = f_id
        obj._possible_names = possible_names

        if not possible_names:
            obj._possible_names = list()

        return obj

    CDU_AND_CSU = (["CDU/CSU", "CDU", "CSU", "Christlich Demokratische Union",
                    "Christlich-Soziale Union",
                    "Fraktion der Christlich Demokratischen Union/Christlich - Sozialen Union",
                    "Fraktion der CDU/CSU (Gast)"])
    SPD = (["SPD", "Sozialdemokratische Partei", "Sozialdemokraten",
            "Sozialdemokrat", "Fraktion der Sozialdemokratischen Partei Deutschlands",
            "Fraktion der SPD (Gast)"])
    DIE_LINKE = (["DIE LINKE", "LINKE", "Linke", "Linkspartei", "Fraktion DIE LINKE."])
    DIE_GRÜNEN = (["BÜNDNIS90/DIE GRÜNEN", "BÜNDNIS 90/DIE GRÜNEN", "BÜNDNISSES 90/DIE GRÜNEN", "Bündnis 90/Die Grünen",
                   "Die Grünen", "Bündnis 90", "Fraktion Bündnis 90/Die Grünen", "Gruppe Bündnis 90/Die Grünen",
                   "Fraktion Die Grünen", "Fraktion Die Grünen/Bündnis 90"])
    AFD = (["AfD", "Alternative für Deutschland"])
    FDP = (["FDP", "Freie Demokratische Partei", "Freie Demokraten",
            "Liberale", "Fraktion der Freien Demokratischen Partei", "Fraktion der FDP (Gast)"])
    NONE = (["Fraktionslos", "fraktionslos"])
    LEGACY = ()

    # historical factions
    # GB_AND_BHE = (["GB/BHE", "BHE", "Gesamtdeutscher Block/Bund der Heimatvertriebenen und Entrechteten",
    #                "Fraktion Deutscher Gemeinschaftsblock der Heimatvertriebenen und Entrechteten",
    #                "Fraktion Gesamtdeutscher Block / Block der Heimatvertriebenen und Entrechteten"])
    # BP = (["BP", "Bayernpartei", "Fraktion Deutsche Partei Bayern", "Fraktion Deutsche Partei/Deutsche Partei Bayern",
    #        "Fraktion Bayernpartei"])
    # DP = (["DP", "Deutsche Partei", "Fraktion Deutsche Partei", "Fraktion DP/DPB (Gast)", "Gruppe Deutsche Partei"])
    # NDP = (["NDP", "Nationaldemokratische Partei",
    #         "National-Demokratische Partei"])
    # KPD = (["KPD", "Kommunistische Partei", "Fraktion der Kommunistischen Partei Deutschlands"])
    # WAV = (["WAV", "Wirtschaftliche Aufbau-Vereinigung"])
    # DZP = (["DZP", "Deutsche Zentrumspartei", "Fraktion Deutsche Zentrums-Partei"])
    # DRP = (["DRP", "Deutsche Reichs-Partei", "Deutsche Rechtspartei", "Fraktion Deutsche Reichspartei/Nationale Rechte",
    #         "Fraktion Deutsche Reichspartei"])
    # DKP = (["DKP", "Deutsche Konservative Partei"])

    # Unassigned Factions
    # "Fraktion der Partei des Demokratischen Sozialismus" "Gruppe der Partei des Demokratischen Sozialismus" "Gruppe der Partei des Demokratischen Sozialismus/Linke Liste"
    # "Fraktion Deutsche Partei/Freie Volkspartei", "Fraktion Freie Volkspartei"
    # Gruppe Kraft/Oberländer
    # Fraktion Wirtschaftliche Aufbauvereinigung
    # Fraktion Demokratische Arbeitsgemeinschaft
    # Fraktion Föderalistische Union
    # Fraktion WAV (Gast)

    @property
    def possible_names(self) -> List[str]:
        """All stored alternative names representing the Enum Value."""
        return self._possible_names.copy()

    @classmethod
    def from_name(cls, name: str) -> "Faction":
        """Utility function to return the first fitting enum value with the
        corresponding name. If the name is not a unique name representative
        in_text should be used to get all possible matches."""

        if name == "":
            return cls.NONE

        for var in cls:
            if name in var._possible_names:
                return var

        logger.warning(
            "received invalid value \"{}\" as faction name! returning Faction.LEGACY...".format(name))

        return Faction.LEGACY

    @classmethod
    def from_mdb_description(cls, mdb_description: str) -> "Faction":
        """Utility function to return the correct Enum Object based on the
        full length faction description text as it is used in the MDB master
        data published by the Bundestag."""

        mapping = {
            "Alternative für Deutschland": Faction.AFD,
            "Fraktion der Christlich Demokratischen Union/Christlich - Sozialen Union": Faction.CDU_AND_CSU,
            "Fraktion der Freien Demokratischen Partei": Faction.FDP,
            "Fraktion der Sozialdemokratischen Partei Deutschlands": Faction.SPD,
            "Fraktion DIE LINKE.": Faction.DIE_LINKE,
            "Fraktion Bündnis 90/Die Grünen": Faction.DIE_GRÜNEN,
            "Fraktion Die Grünen": Faction.DIE_GRÜNEN,
            "Fraktion Die Grünen/Bündnis 90": Faction.DIE_GRÜNEN,

            # legacy stuff
            "Fraktion Deutsche Zentrums-Partei": Faction.LEGACY,
            "Fraktion Deutsche Partei Bayern": Faction.LEGACY,
            "Fraktion Deutsche Reichspartei": Faction.LEGACY,
            "Fraktion Deutsche Partei": Faction.LEGACY,
            "Fraktion Wirtschaftliche Aufbauvereinigung": Faction.LEGACY,
            "Fraktion der Kommunistischen Partei Deutschlands": Faction.LEGACY,
            "Fraktion Deutscher Gemeinschaftsblock der Heimatvertriebenen und Entrechteten": Faction.LEGACY,
            "Fraktion Bayernpartei": Faction.LEGACY,
            "Fraktion Demokratische Arbeitsgemeinschaft": Faction.LEGACY,
            "Fraktion Gesamtdeutscher Block / Block der Heimatvertriebenen und Entrechteten": Faction.LEGACY,
            "Fraktion der Partei des Demokratischen Sozialismus": Faction.LEGACY,
            "Fraktion Deutsche Partei/Freie Volkspartei": Faction.LEGACY,
            "Fraktion Deutsche Partei/Deutsche Partei Bayern": Faction.LEGACY,
            "Fraktion Freie Volkspartei": Faction.LEGACY,
            "Fraktion Föderalistische Union": Faction.LEGACY,
            "Fraktion Deutsche Reichspartei/Nationale Rechte": Faction.LEGACY,

            "Fraktionslos": Faction.NONE
        }

        faction = mapping.get(mdb_description)

        if not faction:
            logger.warning(
                f"from_mdb_description got mdb_description {mdb_description} "
                f"which is not mapped! Falling back to Faction.NONE")
            faction = Faction.NONE

        return faction

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
    # class vars
    _storage_type = "mongodb"
    _mdb_runtime_storage: Dict[str, Dict] = dict()
    _mdb_runtime_storage_mdb_number_index: Dict[str, str] = dict()
    _mdb_runtime_storage_name_index: Dict[Tuple[str, str], str] = dict()

    # instance vars
    speaker_id: str
    mdb_number: Optional[str]
    forename: str
    surname: str
    memberships: List[Tuple[datetime, Optional[datetime], Faction]]
    birthday: Optional[datetime]
    birthplace: Optional[str]
    title: Optional[str]
    job_title: Optional[str]
    debug_info: Optional[Dict]

    @classmethod
    def set_storage_mode(cls, storage_type: str = None):
        if not storage_type:
            storage_type = "mongodb"

        storage_type = storage_type.lower()
        cls._storage_type = storage_type

    @property
    def id(self) -> str:
        return self.speaker_id

    @classmethod
    def find_known_mdbs(cls) -> List["MDB"]:
        def _find_all() -> Optional[List[Dict]]:
            if cls._storage_type == "mongodb":
                return database.find_many("mdb")
            elif cls._storage_type == "runtime":
                return list(cls._mdb_runtime_storage.values())
            else:
                raise RuntimeError("unsupported storage type!")

        mdbs = _find_all()
        logger.debug(f"retrieved {len(mdbs)} MDB entities from {cls._storage_type}")
        return mdbs

    @classmethod
    def find_and_add_in_storage(
            cls,
            forename: str,
            surname: str,
            memberships: List[Tuple[datetime, Optional[datetime], Faction]],
            mdb_number: Optional[str] = None,
            birthday: Optional[datetime] = None,
            birthplace: Optional[str] = None,
            title: Optional[str] = None,
            job_title: Optional[str] = None,
            debug_info: Optional[Dict] = None,
            initial: bool = False,
            created_by: Optional[str] = None) -> "MDB":

        def _find_one(mdb_number=None, forename=None, surname=None) -> Optional[Dict]:
            if cls._storage_type == "mongodb":
                if mdb_number:
                    return database.find_one("mdb", {"mdb_number": mdb_number})
                elif forename or surname:
                    possible_mdbs = database.find_many("mdb", {"forename": forename, "surname": surname})
                    if len(possible_mdbs) == 1:
                        return possible_mdbs[0]
                    elif len(possible_mdbs) > 1:
                        # use latest mdb (not best solution build else will create many duplicates)
                        return _get_latest_mdb(possible_mdbs)

            elif cls._storage_type == "runtime":
                if mdb_number:
                    mdb_idx = cls._mdb_runtime_storage_mdb_number_index.get(mdb_number)
                    return cls._mdb_runtime_storage.get(mdb_idx)
                elif forename or surname:
                    mdb_idx = cls._mdb_runtime_storage_name_index.get((forename, surname))
                    return cls._mdb_runtime_storage.get(mdb_idx)
            else:
                raise RuntimeError("not supported storage_type!")

        def _update_one(key, value, created_by=None):
            if cls._storage_type == "mongodb":
                database.update_one("mdb", {"speaker_id": key}, value, created_by=created_by)
            elif cls._storage_type == "runtime":
                mdb_dict = cls._mdb_runtime_storage.get(key, dict())
                mdb_dict.update(value)

                cls._mdb_runtime_storage[key] = mdb_dict

                name_tuple = (mdb_dict["forename"], mdb_dict["surname"])
                cls._mdb_runtime_storage_name_index[name_tuple] = key

                mdb_number = mdb_dict.get("mdb_number")
                if mdb_number:
                    cls._mdb_runtime_storage_mdb_number_index[mdb_number] = key
            else:
                raise RuntimeError("not supported storage_type!")

        def _get_latest_mdb(possible_mdbs: List[dict]):
            latest_mdb = possible_mdbs[0]
            for mdb in possible_mdbs:
                if datetime.fromisoformat(mdb['modified']) > datetime.fromisoformat(latest_mdb['modified']):
                    latest_mdb = mdb

            return latest_mdb

        mdb = None
        if mdb_number:
            mdb = _find_one(mdb_number=mdb_number)

        if not initial and not mdb:
            mdb = _find_one(forename=forename, surname=surname)

            # if found through name and mdb_number given -> add to document
            if mdb and "mdb_number" not in mdb and mdb_number:
                logging.debug(f"Adding mdb_number '{mdb_number}' to mdb '{mdb['speaker_id']}'")
                mdb['mdb_number'] = mdb_number
                _update_one(mdb["speaker_id"], {"mdb_number": mdb_number})
        if mdb:
            return MDB(**mdb)

        # create new mdb in DB
        if not mdb:
            mdb_id = f"MDB-{uuid.uuid4()}"

            mdb = cls(
                speaker_id=mdb_id,
                mdb_number=mdb_number,
                forename=forename,
                surname=surname,
                memberships=memberships,
                birthday=birthday,
                birthplace=birthplace,
                title=title,
                job_title=job_title,
                debug_info=debug_info)

            _update_one(
                mdb_id,
                json.loads(mdb.json(exclude_none=True, indent=4, ensure_ascii=False)),
                created_by=created_by)

        return mdb

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
    from_paragraph: bool
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

        for mdb_id, mdb in mdb_map.items():
            mdb.memberships = [(m[0], m[1], m[2].value) for m in mdb.memberships]

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
