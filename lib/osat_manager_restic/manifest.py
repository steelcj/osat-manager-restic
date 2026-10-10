"""Reading manager.yaml with the standard library alone.

The manager uses only the standard library, so that it runs on the
Python manage-python installs, which has no PyYAML (decision 0001). This
module reads the strict subset of YAML that manager.yaml uses, and
refuses anything else by name rather than guessing:

- block mappings, nested by indentation with spaces;
- block sequences of scalars (- item) and flow sequences of plain
  scalars ([a, b]);
- block literals (|), for the pinned public key;
- double-quoted, single-quoted and plain scalars; true, false, null and
  integers;
- comments.

Anchors, aliases, tags, flow mappings, folded scalars, complex keys,
tabs and multiple documents are refused.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import List, Optional, Tuple

from .errors import ManagerError

PACKAGE = "osat_manager_restic"
PROJECT = "osat-manager-restic"
MANIFEST = "manager.yaml"

KEY_LINE = re.compile(r"^(?P<key>\"[^\"]*\"|'[^']*'|[A-Za-z0-9_.-]+):(?:\s+(?P<rest>.*))?$")
INTEGER = re.compile(r"^-?[0-9]+$")
REFUSED = ("&", "*", "!", "{", ">", "? ", "%")


class _Line:
    def __init__(self, number: int, indent: int, text: str):
        self.number, self.indent, self.text = number, indent, text


def _strip_comment(text: str) -> str:
    """Remove a trailing comment outside quotes."""
    quote = None
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
    return text.rstrip()


def _scalar(token: str, number: int):
    token = token.strip()
    if token.startswith('"'):
        if not token.endswith('"') or len(token) < 2:
            raise ManagerError(f"line {number}: unterminated string")
        body = token[1:-1]
        out, i = [], 0
        while i < len(body):
            if body[i] == "\\" and i + 1 < len(body):
                nxt = body[i + 1]
                out.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(nxt))
                if out[-1] is None:
                    raise ManagerError(f"line {number}: unsupported escape \\{nxt}")
                i += 2
            else:
                out.append(body[i])
                i += 1
        return "".join(out)
    if token.startswith("'"):
        if not token.endswith("'") or len(token) < 2:
            raise ManagerError(f"line {number}: unterminated string")
        return token[1:-1].replace("''", "'")
    if token.startswith(REFUSED) or token.startswith("|"):
        raise ManagerError(f"line {number}: {token[:1]!r} is outside the "
                           f"YAML subset manager.yaml may use")
    if token.startswith("["):
        if not token.endswith("]"):
            raise ManagerError(f"line {number}: unterminated flow sequence")
        inner = token[1:-1].strip()
        return [_scalar(t, number) for t in inner.split(",")] if inner else []
    if token in ("true", "false"):
        return token == "true"
    if token in ("null", "~", ""):
        return None
    if INTEGER.match(token):
        return int(token)
    return token


def _lines(text: str) -> List[_Line]:
    out = []
    for number, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ManagerError(f"line {number}: tabs are not allowed for "
                               f"indentation")
        if raw.strip() in ("---", "..."):
            raise ManagerError(f"line {number}: one document only")
        out.append(_Line(number, len(raw) - len(raw.lstrip(" ")), raw))
    return out


def loads(text: str):
    lines = _lines(text)
    value, index = _block(lines, 0, 0)
    for line in lines[index:]:
        if _strip_comment(line.text.strip()):
            raise ManagerError(f"line {line.number}: unexpected content")
    return value


def _next_content(lines: List[_Line], index: int) -> int:
    while index < len(lines) and not _strip_comment(lines[index].text.strip()):
        index += 1
    return index


def _block(lines: List[_Line], index: int, indent: int) -> Tuple[object, int]:
    index = _next_content(lines, index)
    if index >= len(lines) or lines[index].indent < indent:
        return None, index
    first = lines[index]
    if _strip_comment(first.text.strip()).startswith("- "):
        return _sequence(lines, index, first.indent)
    return _mapping(lines, index, first.indent)


def _sequence(lines, index, indent):
    items = []
    while True:
        index = _next_content(lines, index)
        if index >= len(lines) or lines[index].indent < indent:
            return items, index
        line = lines[index]
        text = _strip_comment(line.text.strip())
        if line.indent != indent or not text.startswith("- "):
            raise ManagerError(f"line {line.number}: expected a sequence "
                               f"item at indent {indent}")
        item = text[2:]
        if KEY_LINE.match(item):
            raise ManagerError(f"line {line.number}: sequences of mappings "
                               f"are outside the subset")
        items.append(_scalar(item, line.number))
        index += 1


def _mapping(lines, index, indent):
    result = {}
    while True:
        index = _next_content(lines, index)
        if index >= len(lines) or lines[index].indent < indent:
            return result, index
        line = lines[index]
        if line.indent != indent:
            raise ManagerError(f"line {line.number}: unexpected indentation")
        text = _strip_comment(line.text.strip())
        match = KEY_LINE.match(text)
        if not match:
            raise ManagerError(f"line {line.number}: expected key: value")
        key = _scalar(match.group("key"), line.number)
        if key in result:
            raise ManagerError(f"line {line.number}: duplicate key {key!r}")
        rest = match.group("rest")
        if rest is not None and rest.strip() == "|":
            value, index = _literal(lines, index + 1, indent)
        elif rest is None or rest == "":
            value, index = _block(lines, index + 1, indent + 1)
        else:
            value, index = _scalar(rest, line.number), index + 1
        result[key] = value


def _literal(lines, index, parent_indent):
    """A | block: kept lines, each newline-terminated, the trailing blank
    lines clipped to one newline."""
    block: List[str] = []
    indent: Optional[int] = None
    while index < len(lines):
        line = lines[index]
        if line.text.strip():
            if line.indent <= parent_indent:
                break
            if indent is None:
                indent = line.indent
            if line.indent < indent:
                break
            block.append(line.text[indent:])
        else:
            block.append("")
        index += 1
    while block and block[-1] == "":
        block.pop()
    return ("\n".join(block) + "\n") if block else "", index


# ── Finding manager.yaml ────────────────────────────────────────────────────

def manifest_path() -> Path:
    """manager.yaml, installed with the package or at the root of a
    proven checkout, as uc-automa 0019 describes. The manager keeps this
    lookup of its own because it uses the standard library only."""
    spec = importlib.util.find_spec(f"{PACKAGE}.data")
    if spec is not None and spec.submodule_search_locations:
        for location in spec.submodule_search_locations:
            candidate = Path(location) / MANIFEST
            if candidate.is_file():
                return candidate
    package_dir = Path(__file__).resolve().parent
    root = package_dir.parents[1]
    pyproject = root / "pyproject.toml"
    if package_dir == root / "lib" / PACKAGE and pyproject.is_file() and \
            re.search(rf'^name\s*=\s*"{PROJECT}"\s*$',
                      pyproject.read_text(encoding="utf-8"), re.M):
        candidate = root / MANIFEST
        if candidate.is_file():
            return candidate
    raise ManagerError(f"cannot find {MANIFEST}: it is not installed with "
                       f"the package, and {root} is not an {PROJECT} "
                       f"checkout")


def load_manifest(path: Optional[Path] = None) -> dict:
    path = path or manifest_path()
    data = loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("format") != 1:
        raise ManagerError(f"{path}: not a format 1 manager.yaml")
    return data
