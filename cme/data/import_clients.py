#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# script for importing clients for basic authentication

import json
import os

from cme import database

FILENAME = "clients.json"


def import_clients(collection, clients):
    for client in clients:
        result = collection.insert_one(client)
        if result.acknowledged:
            print(f"INFO - Imported {client}")
        else:
            print(f"ERROR - Importing {client} failed")


def main():
    # get attributes file with path
    path = os.path.dirname(__file__)
    clients_filename = f"{path}/{FILENAME}"

    # open file and load clients
    clients_file = open(clients_filename)
    clients = json.load(clients_file)

    db = database.get_db()
    clients_collection = db["client"]

    print(f"INFO - Importing {len(clients)} clients for {os.environ.get('LANDSCAPE')} landscape to DB {db}")
    print(f"INFO - Dropping 'client' collection")
    clients_collection.drop()

    import_clients(clients_collection, clients)
    print(f"INFO - {len(clients)} clients imported into 'client' collection")


if __name__ == '__main__':
    main()
