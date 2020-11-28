#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $SCRIPT_DIR

echo "dropping old cme_* artifacts"
echo "----------------------------------------"
docker container rm cme_mongodb
docker container rm cme_api
docker network rm cme_internal
echo ""

echo "starting services"
echo "----------------------------------------"
docker-compose -f ./docker-compose.prod.yml --env-file ./.env.prod up --build
echo ""
