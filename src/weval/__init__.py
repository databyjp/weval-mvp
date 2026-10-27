"""weval command line: ``weval run``, ``weval check``, ``weval analyse``, and ``weval report``."""

import argparse
from pathlib import Path


def print_diagnostics(found: dict) -> None:
    """Print the Trial-level facts from ``weval.diagnostics.diagnose``."""
    used = found["treatment_used"]
    if used is not None:
        print(f"Treatment: skill {'loaded' if used['skill_loaded'] else 'not loaded'}; "
              f"files named: {', '.join(used['files_named']) or 'none'}")
    if found["deprecations_seen"] is None:
        print("Deprecations seen by the agent: unknown (no agent/trajectory.json)")
    else:
        print(f"Deprecations seen by the agent: {'; '.join(found['deprecations_seen']) or 'none'}")
    print(f"Deprecations in application.log: {'; '.join(found['deprecations_logged']) or 'none'}")


def print_labels(answers: dict) -> None:
    """Print one failed check's labels from ``weval.labels.label``."""
    for question in ("answer_source", "verification"):
        answer = answers[question]
        print(f"     {question.replace('_', ' ')}: {answer['choice']} "
              f"(confidence {answer['confidence']}, {answers['model']})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="weval")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run a Task with an Agent on Modal or local Docker")
    run_parser.add_argument("task", type=Path, help="Task directory, e.g. tasks/build/ecommerce-search")
    run_parser.add_argument("--agent", required=True, help="name from agents.toml")
    run_parser.add_argument("-n", type=int, default=1, help="number of Trials")
    run_parser.add_argument("--local", action="store_true", help="run on the local Docker daemon instead of Modal")
    run_parser.add_argument(
        "--prompt-variant", default="default", help="prompt variant: a file name in the Task's prompts/, without .md"
    )
    run_parser.add_argument("--treatment", help="Treatment: a directory name in treatments/ (default: none, a baseline)")
    check_parser = commands.add_parser("check", help="re-score a retained Trial's snapshot")
    check_parser.add_argument("trial", type=Path, help="Harbor Trial directory")
    check_parser.add_argument("--task", type=Path, help="Task directory (default: from weval.json)")
    analyse_parser = commands.add_parser(
        "analyse", help="analyse the Treatment comparisons that include a retained run, with an LLM"
    )
    analyse_parser.add_argument("run", type=Path, help="run directory under experiment-outputs/")
    report_parser = commands.add_parser("report", help="write the Task catalog and retained runs as HTML pages")
    report_parser.add_argument(
        "outputs", type=Path, nargs="?", default=Path("experiment-outputs"), help="directory of run directories"
    )
    args = parser.parse_args()

    if args.command == "report":
        from weval.report import write_report

        print(write_report(args.outputs))
        return

    # Imported here so `weval --help` does not pay Harbor's import time.
    from weval.labels import label
    from weval.run import analyse_run, check_versions, diagnose, rescore, run

    if args.command == "analyse":
        analyse_run(args.run)
    elif args.command == "run":
        print(run(
            args.task, args.agent, args.n,
            local=args.local, prompt_variant=args.prompt_variant, treatment=args.treatment,
        ))
    else:
        current, recorded = check_versions(args.trial, args.task)
        print(f"check.py {current}, recorded {recorded or 'unversioned'}"
              + ("" if current == recorded else "; scores may differ from weval.json"))
        results = rescore(args.trial, args.task)
        found = diagnose(args.trial, results, args.task)
        labelled = label(args.trial, results)
        seen = {item["check"]: item for item in found["expected_value_seen"] or []}
        for r in results:
            status = "PASS" if r["passed"] else "FAIL"
            kind = "" if r["required"] else " (preferred)"
            print(f"{status} {r['name']}{kind}: {r['notes']}")
            if r["name"] in seen:
                item = seen[r["name"]]
                print(f"     expected {item['expected']}, {'seen' if item['seen'] else 'not seen'} in what the agent was shown")
            if r["name"] in labelled["labels"]:
                print_labels(labelled["labels"][r["name"]])
        print_diagnostics(found)
        if labelled["note"]:
            print(f"Labels: {labelled['note']}")
