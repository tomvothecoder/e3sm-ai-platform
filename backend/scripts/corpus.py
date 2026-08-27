"""Offline curation CLI for acquisition scopes, local captures, and corpus artifacts.

``validate-sources`` validates an upstream acquisition scope (for example,
``corpus/sources.json``).  ``capture`` and ``refresh`` instead require a
separate pinned local capture manifest with local Markdown content.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from e3sm_assist.curation import (
    CurationValidationError,
    capture,
    refresh,
    validate_corpus,
    validate_source_scope,
)


def main() -> int:
    """Run the local-only corpus curation command line interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture_parser = commands.add_parser(
        "capture", help="capture a separate pinned local manifest into a corpus root"
    )
    capture_parser.add_argument("manifest", type=Path)
    capture_parser.add_argument("output", type=Path)
    refresh_parser = commands.add_parser(
        "refresh", help="write a separate candidate corpus and changes.json"
    )
    refresh_parser.add_argument(
        "snapshot", type=Path, help="existing corpus root containing snapshot.json"
    )
    refresh_parser.add_argument("manifest", type=Path)
    refresh_parser.add_argument("output", type=Path)
    validate_parser = commands.add_parser(
        "validate", help="validate corpus artifacts without network access"
    )
    validate_parser.add_argument("root", type=Path)
    validate_parser.add_argument(
        "--require-approved", action="store_true", help="require a hash-bound approved review"
    )
    source_scope_parser = commands.add_parser(
        "validate-sources", help="validate an offline acquisition scope, not a capture manifest"
    )
    source_scope_parser.add_argument(
        "path", type=Path, help="acquisition scope JSON, e.g. corpus/sources.json"
    )
    args = parser.parse_args()
    try:
        if args.command == "capture":
            capture(args.manifest, args.output)
        elif args.command == "refresh":
            refresh(args.snapshot, args.manifest, args.output)
        elif args.command == "validate-sources":
            failures = validate_source_scope(args.path)
            if failures:
                parser.error("; ".join(failures))
        else:
            failures = validate_corpus(args.root, require_approved=args.require_approved)
            if failures:
                parser.error("; ".join(failures))
    except CurationValidationError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
