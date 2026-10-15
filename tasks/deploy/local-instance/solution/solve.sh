#!/bin/sh
set -eu

cp /solution/docker-compose.yaml /app/

cd /app
docker compose up --detach --wait --wait-timeout 180
python /solution/create_collection.py
