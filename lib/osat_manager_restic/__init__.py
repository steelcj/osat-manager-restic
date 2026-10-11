"""manage-restic: a user-space manager for restic, the OSAT pilot."""

import sys

# The manager leaves nothing behind, and that includes bytecode caches:
# a Python installed in the user's own account, as manage-python installs
# it, would otherwise cache each module the manager imports inside that
# Python. Set before anything else is imported.
sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402


def _version() -> str:
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover
        return "unknown"
    try:
        return version("osat-manager-restic")
    except PackageNotFoundError:
        here = Path(__file__).resolve()
        for candidate in (here.parents[2] / "VERSION", here.parent / "VERSION"):
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8").strip()
        return "unknown"


__version__ = _version()
