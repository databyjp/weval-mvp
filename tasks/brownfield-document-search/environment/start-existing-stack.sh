#!/bin/sh
set -eu

# Only the evaluator's startup path creates the baseline. Verification must
# inspect the agent's final volume without running this script again.
docker compose --project-directory /app up --detach --wait --wait-timeout 180
python /app/scripts/seed_source.py
uvicorn main:app --app-dir /app --host 127.0.0.1 --port 8000 \
  >/tmp/source-application.log 2>&1 &
printf '%s\n' "$!" >/tmp/source-application.pid

# The source application and its client must answer a real search before the
# agent gets a Trial. A broken evaluator baseline is not an agent failure.
ready=0
for _attempt in $(seq 1 60); do
  if curl --fail --silent --show-error \
    'http://127.0.0.1:8000/search?query=bread&limit=1' 2>/dev/null \
    | python -c 'import json, sys; assert json.load(sys.stdin)["items"]'; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  cp /tmp/source-application.log /logs/verifier/source-application.log
  exit 1
fi
touch /tmp/weval-source-ready

exec "$@"
