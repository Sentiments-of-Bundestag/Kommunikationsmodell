#!/bin/bash
# start CME api locally in developer mode

# go to working folder
cd "$(dirname "$0")" || exit

pip install -r requirements.txt

# set clients and passwords for API auth
# read factions from .json

uvicorn cme.api.api:app --reload --log-level=info --port 9001
