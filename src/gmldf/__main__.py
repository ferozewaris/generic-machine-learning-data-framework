"""Command-line entry point; commands expose only implemented behavior."""

import argparse
import json
import sys
from pathlib import Path

from gmldf.core.config import ConfigError, load_config, validate_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gmldf")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate config offline; no provider access")
    validate.add_argument("--config", type=Path, required=True)
    validate.add_argument("--profile")
    validate.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        workflow = load_config(args.config)
        if args.profile is not None:
            config = workflow.model_dump(exclude_unset=True)
            config["execution"]["profile"] = args.profile
            workflow = validate_config(config)
    except ConfigError as exc:
        print(
            json.dumps({"error": {"code": exc.code, "path": exc.path, "reason": exc.reason}}),
            file=sys.stderr,
        )
        return 2
    report = {
        "valid": True,
        "scope": "configuration",
        "name": workflow.name,
        "kind": workflow.kind,
        "engine": workflow.engine,
        "profile": workflow.execution.profile,
        "capabilities_checked": False,
    }
    content = json.dumps(report, indent=2) + "\n"
    if args.output is not None:
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(content)
        except OSError:
            print(
                json.dumps(
                    {"error": {"code": "OUTPUT_INCOMPLETE", "reason": "cannot_write_report"}}
                ),
                file=sys.stderr,
            )
            return 1
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
