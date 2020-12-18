import json
import uuid
from pathlib import Path
from datetime import datetime

from cme import database

from cme.domain import Faction, MDB


def update_mdbs_from_crawler(file: Path):
    try:
        if file:
            persons = json.loads(open(file.absolute(), "r").read())
        else:
            persons = database.get_crawler_db()["person"].find({})
    except:
        raise ConnectionError("Can't connect to remote crawler db. If you're developing locally you must specify a equivalent "
              "json with --file as fallback.")

    for p in persons:
        memberships = []
        for timeframe in p["fraktionen"]:
            austrittsdatum = None
            if 'austrittsDatum' in timeframe:
                austrittsdatum = get_safe_datetime(timeframe['austrittsDatum'])

            eintrittsdatum = get_safe_datetime(timeframe['eintrittsDatum'])
            membership = (eintrittsdatum, austrittsdatum, Faction.from_mdb_description(timeframe["beschreibung"]))

            memberships.append(membership)

        # will auto create MDB if not yet existent
        MDB.find_and_add_in_storage(p['vorname'], p['nachname'], memberships, p['_id'],
                                    get_safe_datetime(p['geburtsdatum']), p['geburtsort'], p['titel'], p['beruf'],
                                    initial=True)

        #database.update_one("mdb", {"mdb_number": mdb_number}, p)


def get_safe_datetime(date):
    if not isinstance(date, datetime):
        date = datetime.fromisoformat(date)
    return date



def init_mdb_collection(file: Path):
    database.delete_many("mdb", {})
    update_mdbs_from_crawler(file)
