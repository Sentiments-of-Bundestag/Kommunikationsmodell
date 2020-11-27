#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd $SCRIPT_DIR

echo "dropping old cme_* artifacts"
echo "----------------------------------------"
docker container rm cme_mongodb
docker network rm cme_internal
docker volume rm cme_db-volume
docker volume rm cme_configdb-volume
echo ""

echo "starting services"
echo "----------------------------------------"
docker-compose --env-file ./.env.dev up 
echo ""

echo "dropping cme_* services"
echo "----------------------------------------"
docker container rm cme_mongodb
docker network rm cme_internal
docker volume rm cme_db-volume
docker volume rm cme_configdb-volume

