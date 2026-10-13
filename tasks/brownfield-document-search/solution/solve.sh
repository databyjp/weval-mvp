#!/bin/sh
set -eu

cd /app

# Preserve the Compose project's named volume while advancing one Weaviate
# minor line per restart. The source and inference model stay unchanged.
for version in \
  1.31.22 1.32.27 1.33.18 1.34.20 1.35.23 \
  1.36.23 1.37.17 1.38.17 1.39.7; do
  python - "$version" <<'PY'
import re
import sys
from pathlib import Path

path = Path('/app/docker-compose.yaml')
source = path.read_text()
updated, count = re.subn(
    r'(image: cr\.weaviate\.io/semitechnologies/weaviate:)1\.\d+\.\d+',
    rf'\g<1>{sys.argv[1]}',
    source,
)
if count != 1:
    raise RuntimeError('source Compose file must have one Weaviate image')
path.write_text(updated)
PY
  docker compose up --detach --wait --wait-timeout 180
  python - "$version" <<'PY'
import json
import os
import sys
import urllib.request

base = f"http://{os.environ['WEAVIATE_HTTP_HOST']}:{os.environ['WEAVIATE_HTTP_PORT']}"
with urllib.request.urlopen(f'{base}/v1/meta', timeout=30) as response:
    actual = json.load(response)['version']
if actual != sys.argv[1]:
    raise RuntimeError(f'expected Weaviate {sys.argv[1]}, got {actual}')
PY
done

python - <<'PY'
from pathlib import Path
path = Path('/app/requirements.txt')
source = path.read_text()
if source.count('weaviate-client==4.12.1') != 1:
    raise RuntimeError('source Python client pin has changed')
path.write_text(source.replace('weaviate-client==4.12.1', 'weaviate-client==4.23.1'))
PY
uv pip install --system -r /app/requirements.txt

# Restart the application so it imports the upgraded client package.
kill "$(cat /tmp/source-application.pid)"
uvicorn main:app --app-dir /app --host 127.0.0.1 --port 8000 \
  >/tmp/source-application.log 2>&1 &
printf '%s\n' "$!" >/tmp/source-application.pid
