"""weval command line: ``weval run`` and ``weval check``."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="weval")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run a Task under a Condition on Modal")
    run_parser.add_argument("task", type=Path, help="Task directory, e.g. tasks/greenfield-ecommerce-search")
    run_parser.add_argument("--condition", required=True, help="name from conditions.toml")
    run_parser.add_argument("-n", type=int, default=1, help="number of Trials")
    check_parser = commands.add_parser("check", help="re-score a retained Trial's snapshot")
    check_parser.add_argument("trial", type=Path, help="Harbor Trial directory")
    check_parser.add_argument("--task", type=Path, help="Task directory (default: from weval.json)")
    args = parser.parse_args()

    # Imported here so `weval --help` does not pay Harbor's import time.
    from weval.run import rescore, run

    if args.command == "run":
        print(run(args.task, args.condition, args.n))
    else:
        for r in rescore(args.trial, args.task):
            status = "PASS" if r["passed"] else "FAIL"
            kind = "" if r["required"] else " (preferred)"
            print(f"{status} {r['name']}{kind}: {r['notes']}")
