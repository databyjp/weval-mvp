"""Shared Task verifier: snapshot the live stack, then score the snapshot.

Harbor runs this inside the Trial environment as ``/tests/verify.py``, beside
the Task's ``snapshot.py`` and ``check.py``. It uses only the standard library
so it runs on any Task image with Python 3.

Flow: start the submitted Compose stack (unless the Task sets
``WEVAL_KEEP_STACK=1`` because the agent's live stack is the thing under test,
or the submitted ``/app`` has no ``docker-compose.yaml``),
start the submitted app on ``APP_PORT`` when the Task sets
``WEVAL_START_APP=1``, call ``snapshot.snapshot(app_url)`` (``None`` without an
app), add the prompt variant named in ``prompt_variant`` beside this file, then
score it with ``check.py``. Everything is written to ``/logs/verifier``.
A stack, app, or snapshot failure is recorded in the snapshot (``error`` plus
``error_stage``: ``stack``, ``app``, or ``snapshot``) and scored as failing
checks; it is not a verifier crash.
"""

import importlib
import json
import os
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path
from types import ModuleType

APP_DIR = Path("/app")
LOG_DIR = Path("/logs/verifier")
# Not 8000: the agent may have left its own server running there.
APP_PORT = 18000


def score(check: ModuleType, snapshot: dict) -> list[dict]:
    """Run every check in a Task's ``check.py`` against one snapshot.

    ``check.REQUIRED`` and ``check.PREFERRED`` list check functions. Each takes
    the snapshot and passes by returning (optionally a note string) or fails by
    raising ``AssertionError`` whose message names the constraint. Any other
    exception, such as a missing snapshot section, fails the check with a
    "could not evaluate" note instead of aborting scoring.

    A Task with prompt variants also defines ``PROMPT_VARIANT_REQUIRED`` and
    ``PROMPT_VARIANT_PREFERRED``, mapping each prompt variant name to more
    check functions; the snapshot's ``prompt_variant`` picks them. A snapshot
    without ``prompt_variant`` is the ``default`` prompt variant.
    """
    prompt_variant = snapshot.get("prompt_variant", "default")
    required_checks = check.REQUIRED + getattr(
        check, "PROMPT_VARIANT_REQUIRED", {}
    ).get(prompt_variant, [])
    preferred_checks = check.PREFERRED + getattr(
        check, "PROMPT_VARIANT_PREFERRED", {}
    ).get(prompt_variant, [])
    results = []
    for required, functions in ((True, required_checks), (False, preferred_checks)):
        for function in functions:
            try:
                passed, notes = True, function(snapshot) or ""
            except AssertionError as error:
                passed, notes = False, str(error)
            except Exception as error:  # noqa: BLE001
                passed, notes = False, f"could not evaluate: {error!r}"
            if not passed and "error" in snapshot:
                notes += " (snapshot failed; see snapshot.json)"
            results.append(
                {
                    "name": function.__name__.replace("_", "-"),
                    "required": required,
                    "passed": passed,
                    "notes": notes,
                    "description": (function.__doc__ or "").strip(),
                }
            )
    return results


def reward(results: list[dict]) -> int:
    """Return 1 when every required check passed, else 0."""
    return int(all(r["passed"] for r in results if r["required"]))


def _compose(*args: str, timeout: int = 240) -> subprocess.CompletedProcess[str]:
    # check=False: callers read returncode and stderr to report compose failures.
    return subprocess.run(
        ["docker", "compose", "--file", str(APP_DIR / "docker-compose.yaml"), *args],
        check=False,
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _start_app() -> subprocess.Popen[bytes]:
    """Start the submitted ``main:app`` and wait up to 120 s for it to answer HTTP."""
    log = (LOG_DIR / "application.log").open("wb")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--app-dir",
            str(APP_DIR),
            "--host",
            "127.0.0.1",
            "--port",
            str(APP_PORT),
        ],
        cwd=APP_DIR,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f"app exited with code {process.returncode}")
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{APP_PORT}/openapi.json", timeout=2
            )
            return process
        except OSError:
            time.sleep(1)
    raise RuntimeError("app did not answer HTTP within 120 s")


def main() -> None:
    """Snapshot and score the Trial, always writing reward, snapshot, and checks."""
    sys.path.insert(0, str(Path(__file__).parent))
    keep_stack = os.environ.get("WEVAL_KEEP_STACK") == "1"
    has_stack = (APP_DIR / "docker-compose.yaml").exists()
    start_app = os.environ.get("WEVAL_START_APP") == "1"
    app = None
    # The stage records where the failure happened: "stack" and "app" are the
    # agent's submission failing to start; "snapshot" is snapshot.py raising,
    # usually on the agent's broken stack, sometimes on a scorer bug.
    stage = "stack"
    try:
        if has_stack and not keep_stack:
            up = _compose("up", "--detach", "--wait", "--wait-timeout", "180")
            if up.returncode != 0:
                raise RuntimeError(f"docker compose up failed:\n{up.stdout}{up.stderr}")
        app_url = None
        stage = "app"
        if start_app:
            app = _start_app()
            app_url = f"http://127.0.0.1:{APP_PORT}"
        stage = "snapshot"
        snapshot = importlib.import_module("snapshot").snapshot(app_url)
    except Exception:  # noqa: BLE001
        snapshot = {"error": traceback.format_exc(), "error_stage": stage}
    finally:
        if app is not None:
            app.terminate()
        if has_stack:
            logs = _compose("logs", "--no-color", "--timestamps", timeout=60)
            (LOG_DIR / "docker-compose.log").write_text(logs.stdout + logs.stderr)
            # Matters for local Docker, where the stack would outlive the Trial.
            _compose("down", "--volumes", timeout=120)

    # Recorded even on failure, so the failed snapshot is scored on the
    # prompt variant's checks too.
    snapshot["prompt_variant"] = (
        Path(__file__).with_name("prompt_variant").read_text().strip()
    )
    (LOG_DIR / "snapshot.json").write_text(json.dumps(snapshot, indent=1))
    results = score(importlib.import_module("check"), snapshot)
    (LOG_DIR / "checks.json").write_text(json.dumps(results, indent=1))
    (LOG_DIR / "reward.txt").write_text(str(reward(results)))
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        kind = "" if r["required"] else " (preferred)"
        print(f"{status} {r['name']}{kind}: {r['notes']}")


if __name__ == "__main__":
    main()
