#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $SCRIPT_DIR

VERSION=$(cat setup.py | grep -oP 'version="\K[^"]+')

docker image rm cme:latest

docker build \
  -t cme:latest -t cme:$VERSION \
  .

docker save --output cme_latest.tar cme:latest