import json
import uuid
from pathlib import Path

from cme import database
from cme.domain import Faction


def update_mdbs_from_crawler(file: Path):
    try:
        if file:
            persons = json.loads(open(file.absolute(), "r").read())
        else:
            persons = database.get_crawler_db()["person"].find({})
    except error:


    for p in persons:
        for timeframe in p["fraktionen"]:
            timeframe["id"] = Faction.from_name(timeframe["beschreibung"]).value

        mdb_number = p["_id"]
        p["_id"] = str(uuid.uuid4())
        p["mdb_number"] = mdb_number

        database.update_one("mdb", {"mdb_number": mdb_number}, p)


def init_mdb_collection(file: Path):
    database.delete_many("mdb", {})
    update_mdbs_from_crawler(file)
