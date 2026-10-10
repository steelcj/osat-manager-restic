"""Everything that differs between Linux, macOS and Windows, in one place:
which build to download, where things are installed, how aliases are
written, and how installed files are protected."""

from __future__ import annotations

import os
import platform
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from .errors import ManagerError

SYSTEMS = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}
HOME_VAR = "OSAT_RESTIC_HOME"         # overrides the install root
BIN_VAR = "OSAT_BIN_DIR"              # overrides the alias directory
WINDOWS_VAR = re.compile(r"%([A-Za-z0-9_]+)%")


def current_system() -> str:
    system = SYSTEMS.get(platform.system())
    if system is None:
        raise ManagerError(f"{platform.system()} is not a platform this "
                           f"manager supports")
    return system


def current_arch(manifest: dict, system: str,
                 machine: Optional[str] = None) -> str:
    machine = machine or platform.machine()
    arches = manifest["platforms"][system]["arch"]
    if machine not in arches:
        raise ManagerError(f"restic publishes no {system} build this manager "
                           f"maps for {machine!r}; known: "
                           f"{', '.join(sorted(arches))}")
    return arches[machine]


def expand(text: str, environ: Mapping[str, str]) -> Path:
    def var(match):
        name = match.group(1)
        if name not in environ:
            raise ManagerError(f"%{name}% is not set")
        return environ[name]
    text = WINDOWS_VAR.sub(var, text)
    if text.startswith("~"):
        home = environ.get("HOME") or environ.get("USERPROFILE")
        text = (home or str(Path.home())) + text[1:]
    return Path(text)


@dataclass
class Paths:
    root: Path
    bin_dir: Path
    windows: bool

    @property
    def versions(self) -> Path:
        return self.root / "versions"

    @property
    def archive(self) -> Path:
        return self.root / "archive"

    @property
    def staging(self) -> Path:
        return self.root / "staging"

    @property
    def manager(self) -> Path:
        return self.root / "manager"

    @property
    def state(self) -> Path:
        return self.root / "state.json"

    def binary(self, version: str) -> Path:
        name = "restic.exe" if self.windows else "restic"
        return self.versions / version / name

    def launcher(self, name: str) -> Path:
        return self.bin_dir / (f"{name}.cmd" if self.windows else name)


def resolve_paths(manifest: dict, system: str,
                  environ: Mapping[str, str] = os.environ) -> Paths:
    root = environ.get(HOME_VAR) or None
    bin_dir = environ.get(BIN_VAR) or None
    root_path = Path(root) if root else expand(manifest["install_root"][system],
                                               environ)
    bin_path = Path(bin_dir) if bin_dir else expand(manifest["bin_dir"][system],
                                                    environ)
    return Paths(root_path, bin_path, system == "windows")


# ── Protection ──────────────────────────────────────────────────────────────

def protect(path: Path) -> None:
    """Make an installed file or directory tree read-only."""
    for item in sorted(path.rglob("*"), reverse=True) if path.is_dir() else []:
        _read_only(item)
    _read_only(path)


def _read_only(path: Path) -> None:
    """Owner-only and read-only: 0o500 for directories and executables,
    0o400 for other files. On Windows, the read-only attribute."""
    if os.name == "nt":
        if path.is_file():
            path.chmod(stat.S_IREAD)
        return
    executable = path.is_dir() or path.stat().st_mode & stat.S_IXUSR
    path.chmod(0o500 if executable else 0o400)


def unprotect(path: Path) -> None:
    """Make a protected tree writable again, so the manager can remove it."""
    if not path.exists():
        return
    items = [path] + (sorted(path.rglob("*")) if path.is_dir() else [])
    for item in items:
        mode = item.stat().st_mode
        item.chmod(mode | stat.S_IWRITE | stat.S_IREAD |
                   (stat.S_IEXEC if item.is_dir() else 0))


def remove_tree(path: Path) -> None:
    import shutil
    if path.exists():
        unprotect(path)
        shutil.rmtree(path)
