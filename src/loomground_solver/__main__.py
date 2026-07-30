"""Command-line transport for the vendor-neutral reasoning protocol."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .service import default_service
from .loomground import reason as reason_loomground


def _read_json(path: str) -> dict:
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def _write_json(value: dict, path: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path:
        Path(path).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="loomground-solver")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("manifest", help="print the supported protocol manifest")
    verify = commands.add_parser("verify", help="verify a reasoning request")
    verify.add_argument("request", help="request JSON path, or - for stdin")
    verify.add_argument("-o", "--output", help="write result JSON to this path")
    loomground = commands.add_parser("loomground", help="evaluate a Loomground .lg program")
    loomground.add_argument("source", help="Loomground source path")
    loomground.add_argument("--transport", help="optional transport JSON path")
    loomground.add_argument("-o", "--output", help="write result JSON to this path")
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    service = default_service()
    try:
        if args.command == "manifest":
            _write_json(service.manifest(), None)
        elif args.command == "verify":
            _write_json(service.verify(_read_json(args.request)), args.output)
        else:
            source = Path(args.source).read_text(encoding="utf-8")
            transport = _read_json(args.transport) if args.transport else None
            _write_json(reason_loomground(source, transport), args.output)
    except (OSError, ValueError, KeyError, TypeError, RecursionError, json.JSONDecodeError) as exc:
        print(f"loomground-solver: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
