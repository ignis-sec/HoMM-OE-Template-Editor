#!/usr/bin/env python3
"""CLI: process a game `Core/` folder into the editor's catalog snapshot."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from templategen.catalog.builder import CatalogBuildError, build_snapshot, write_snapshot

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

DEFAULT_CORE = Path("game-data/Core")
DEFAULT_OUTPUT = Path("data/catalog.json")
DEFAULT_ICON_DIR = Path("src/templategen/img/items")


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
    parser.add_argument(
        "--icon-dir",
        type=Path,
        default=DEFAULT_ICON_DIR,
        help=f"Where to copy referenced artifact icon PNGs (default: {DEFAULT_ICON_DIR})",
    )
    parser.add_argument(
        "--texture-root",
        type=Path,
        default=None,
        help="Source folder for icon PNGs (default: <core_path>/../Assets/Texture2D)",
    )
    parser.add_argument(
        "--no-icons",
        action="store_true",
        help="Skip copying artifact icon images",
    )
    args = parser.parse_args(argv)

    try:
        snapshot = build_snapshot(
            args.core_path,
            item_icon_target_dir=None if args.no_icons else args.icon_dir,
            texture_root=args.texture_root,
        )
    except CatalogBuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_snapshot(snapshot, args.output)
    print(
        f"wrote {args.output}: "
        f"{len(snapshot['sids'])} sids, "
        f"{len(snapshot['content_lists'])} content lists, "
        f"{len(snapshot['content_pools'])} content pools, "
        f"{len(snapshot['biomes'])} biomes, "
        f"{len(snapshot['artifacts'])} artifacts"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
