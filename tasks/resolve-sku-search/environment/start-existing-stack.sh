#!/bin/sh
set -eu

# Only the evaluator's startup path seeds the catalog. Verification must
# inspect the agent's final volume without running this script again.
docker compose --project-directory /app up --detach --wait --wait-timeout 180
python /opt/weval/seed_catalog.py
uvicorn main:app --app-dir /app --host 127.0.0.1 --port 8000 \
  >/tmp/application.log 2>&1 &
printf '%s\n' "$!" >/tmp/application.pid

# The Trial is only valid if the reported failure reproduces through the app:
# another product ranks above ZXQ-9917. A broken baseline is not an agent failure.
reproduced=0
for _attempt in $(seq 1 60); do
  if curl --fail --silent 'http://127.0.0.1:8000/search?query=ZXQ-9917&limit=5' 2>/dev/null \
    | python -c 'import json, sys; skus = [i["sku"] for i in json.load(sys.stdin)["items"]]; assert "ZXQ-9917" in skus[1:], skus'; then
    reproduced=1
    break
  fi
  sleep 2
done
if [ "$reproduced" -ne 1 ]; then
  cp /tmp/application.log /logs/verifier/source-application.log
  exit 1
fi
touch /tmp/weval-catalog-ready

exec "$@"
