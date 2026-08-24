"""Command-line entry point for the source-only Agency distribution."""

from __future__ import annotations

import argparse
import os
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path


def _version() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    try:
        return package_version("agency-kit")
    except PackageNotFoundError:
        return "0.0.0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agency",
        description="Local-first web workspace for verifiable agent workflows.",
    )
    parser.add_argument("--version", action="version", version=_version())
    commands = parser.add_subparsers(dest="command")
    start = commands.add_parser("start", help="start the local web application")
    start.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    start.add_argument("--port", type=int, default=8800, help="listen port (default: 8800)")
    start.add_argument(
        "--project-root",
        action="append",
        default=[],
        metavar="PATH",
        help="allow project file access under PATH; may be repeated",
    )
    return parser


def _start_server(host: str, port: int, project_roots: list[str]) -> int:
    from maestro.project_access import configure_project_roots

    configure_project_roots(project_roots)
    os.environ["AGENCY_HOST"] = host
    os.environ["AGENCY_PORT"] = str(port)

    from maestro.remote import require_remote_auth

    require_remote_auth(host)
    from maestro.flask_app import run_server

    run_server(host=host, port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "start":
        if not 1 <= args.port <= 65535:
            parser.error("--port must be between 1 and 65535")
        return _start_server(args.host, args.port, args.project_root)
    parser.error(f"unknown command: {args.command}")
    return 2
