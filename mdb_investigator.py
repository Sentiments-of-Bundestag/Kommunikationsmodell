import json
from collections import defaultdict

with open("./resources/plenarprotokolle/group_1/splitted/mdb.json") as f:
    mdb = json.load(f)

    print(f"mdb file contains a total of {len(mdb)}")

    mdb = {
        k: v
        for k, v in mdb.items()
        if "debug_info" in v}

    print(f"mdb file contains a total of with a debug_info key {len(mdb)}")

    mdbs_with_lower_forename = {k: v for k, v in mdb.items() if v["forename"][0].islower()}
    print(f"mdb file contains {len(mdbs_with_lower_forename)} with a forename starting with a lower letter")

    mdb_dot_start = {k: v for k, v in mdb.items() if v["forename"].startswith(".")}
    print(f"mdb file contains {len(mdb_dot_start)} with a forename starting with a '.'")

    mdb_gaulands = {k: v for k, v in mdb.items() if v["surname"] == "Gauland"}
    print(f"mdb file contains {len(mdb_gaulands)} gaulands")

    mdbs_by_surname = defaultdict(list)
    for mdb_id, data in mdb.items():
        mdbs_by_surname[data["surname"]].append(data)

    mdbs_with_same_surname = {k: v for k, v in mdbs_by_surname.items() if len(v) > 1}
    print(f"mdb file contains {len(mdbs_with_same_surname)} mdbs with the same surname")
