#!/usr/bin/env python3
"""CLI: process a game `Core/` folder into the editor's catalog snapshot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from templategen.catalog.builder import CatalogBuildError, build_snapshot, write_snapshot

DEFAULT_CORE = Path("game-data/Core")
DEFAULT_OUTPUT = Path("data/catalog.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the editor's reference catalog from the game's Core/ folder.")
    parser.add_argument(
        "core_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CORE,
        help=f"Path to the game's Core folder (default: {DEFAULT_CORE})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Snapshot output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args(argv)

    try:
        snapshot = build_snapshot(args.core_path)
    except CatalogBuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_snapshot(snapshot, args.output)
    print(
        f"wrote {args.output}: "
        f"{len(snapshot['sids'])} sids, "
        f"{len(snapshot['content_lists'])} content lists, "
        f"{len(snapshot['content_pools'])} content pools, "
        f"{len(snapshot['biomes'])} biomes"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
