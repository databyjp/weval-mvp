"""weval command line: ``weval run`` and ``weval check``."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(prog="weval")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run a Task with an Agent on Modal or local Docker")
    run_parser.add_argument("task", type=Path, help="Task directory, e.g. tasks/build/ecommerce-search")
    run_parser.add_argument("--agent", required=True, help="name from agents.toml")
    run_parser.add_argument("-n", type=int, default=1, help="number of Trials")
    run_parser.add_argument("--local", action="store_true", help="run on the local Docker daemon instead of Modal")
    run_parser.add_argument(
        "--variant", default="default", help="prompt variant: a file name in the Task's prompts/, without .md"
    )
    check_parser = commands.add_parser("check", help="re-score a retained Trial's snapshot")
    check_parser.add_argument("trial", type=Path, help="Harbor Trial directory")
    check_parser.add_argument("--task", type=Path, help="Task directory (default: from weval.json)")
    args = parser.parse_args()

    # Imported here so `weval --help` does not pay Harbor's import time.
    from weval.run import rescore, run

    if args.command == "run":
        print(run(args.task, args.agent, args.n, local=args.local, variant=args.variant))
    else:
        for r in rescore(args.trial, args.task):
            status = "PASS" if r["passed"] else "FAIL"
            kind = "" if r["required"] else " (preferred)"
            print(f"{status} {r['name']}{kind}: {r['notes']}")
