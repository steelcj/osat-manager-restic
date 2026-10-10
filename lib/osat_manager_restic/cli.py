"""The manage-restic command.

    manage-restic --install [VERSION]   Install a version, verified, and make it active
    manage-restic --switch VERSION      Make an installed version active
    manage-restic --status              Show the active, installed and archived versions and aliases
    manage-restic --remove VERSION      Remove an installed version; its verified archive is kept
    manage-restic --alias OLD=NEW       Rename an alias
    manage-restic --self-install        Install the manager itself, so it works from any directory
    manage-restic --uninstall [--yes]   Remove everything the manager owns
    manage-restic --version             Show this manager's version
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from . import __version__
from .errors import ManagerError
from .manager import Manager
from .manifest import load_manifest, manifest_path
from .platforms import current_arch, current_system, resolve_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage-restic",
        description="Manage user-space installations of restic, verified "
                    "against its signed checksums.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", nargs="?", const="", metavar="VERSION",
                       help="Install a version and make it active "
                            "(default: the latest release).")
    group.add_argument("--switch", metavar="VERSION",
                       help="Make an installed version active.")
    group.add_argument("--status", action="store_true",
                       help="Show versions and aliases.")
    group.add_argument("--remove", metavar="VERSION",
                       help="Remove an installed version; its archive is kept.")
    group.add_argument("--alias", metavar="OLD=NEW", help="Rename an alias.")
    group.add_argument("--self-install", action="store_true",
                       help="Install the manager itself.")
    group.add_argument("--uninstall", action="store_true",
                       help="Remove everything the manager owns.")
    group.add_argument("--version", action="version",
                       version=f"manage-restic {__version__}")
    parser.add_argument("--yes", action="store_true",
                        help="--uninstall: do not ask for confirmation.")
    return parser


def root_guard() -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        raise ManagerError("manage-restic installs into a user's own "
                           "directories; run it as that user, not as root")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root_guard()
        manifest = load_manifest()
        system = current_system()
        manager = Manager(manifest, resolve_paths(manifest, system), system,
                          current_arch(manifest, system))
        if args.install is not None:
            manager.install(args.install or None)
        elif args.switch:
            manager.switch(args.switch)
        elif args.status:
            print(manager.status())
        elif args.remove:
            manager.remove(args.remove)
        elif args.alias:
            manager.rename_alias(args.alias)
        elif args.self_install:
            manager.self_install(manifest_path())
        elif args.uninstall:
            if not args.yes:
                answer = input(f"Remove {manager.paths.root}, including the "
                               f"verified archive, and every manage-restic "
                               f"launcher? [y/N] ").strip().lower()
                if answer != "y":
                    print("[manage-restic] nothing removed")
                    return 1
            manager.uninstall()
        return 0
    except ManagerError as exc:
        print(f"[manage-restic ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
