#!/bin/sh
set -eu

cp \
  /solution/docker-compose.yaml \
  /solution/main.py \
  /solution/search_backend.py \
  /app/

cd /app
docker compose up --detach --wait --wait-timeout 180
