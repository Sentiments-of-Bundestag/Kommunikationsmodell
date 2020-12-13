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
            if 'austrittsDatum' in timeframe:
                austrittsdatum = datetime.strptime(timeframe['austrittsDatum'], '%Y-%m-%dT%H:%M:%S%z')
            else:
                austrittsdatum = None

            membership = (datetime.strptime(timeframe['eintrittsDatum'], '%Y-%m-%dT%H:%M:%S%z'), austrittsdatum, Faction.from_name(timeframe["beschreibung"]))
            memberships.append(membership)

        # will auto create MDB if not yet existent
        MDB.find_and_add_in_storage(p['vorname'], p['nachname'], memberships, p['_id'], datetime.strptime(p['geburtsdatum'], '%Y-%m-%dT%H:%M:%S%z'), p['geburtsort'], p['titel'], p['beruf'], initial=True)

        #database.update_one("mdb", {"mdb_number": mdb_number}, p)


def init_mdb_collection(file: Path):
    database.delete_many("mdb", {})
    update_mdbs_from_crawler(file)
