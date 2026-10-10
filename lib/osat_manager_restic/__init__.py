"""manage-restic: a user-space manager for restic, the OSAT pilot."""

from pathlib import Path


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
