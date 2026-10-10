"""Downloads from restic's release pages, with retries for transient
errors and a clear message when a version or build was never published."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .errors import ManagerError

USER_AGENT = "manage-restic (osat-manager-restic)"
ATTEMPTS = 3


class NotPublished(ManagerError):
    """Upstream has no such file: the version or build does not exist."""


class Network:
    """Fetches URLs. Tests replace it with one that reads local files or
    refuses every request, to prove offline behaviour."""

    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

    def fetch(self, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        for attempt in range(1, ATTEMPTS + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as r:
                    return r.read()
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    raise NotPublished(f"not published upstream: {url}") from None
                if exc.code < 500 or attempt == ATTEMPTS:
                    raise ManagerError(f"download failed ({exc.code}): {url}") from None
            except (urllib.error.URLError, OSError) as exc:
                if attempt == ATTEMPTS:
                    raise ManagerError(f"download failed: {url}: {exc}") from None
            time.sleep(2 * attempt)
        raise ManagerError(f"download failed: {url}")  # pragma: no cover

    def latest_version(self, api_url: str) -> str:
        data = json.loads(self.fetch(api_url).decode("utf-8"))
        tag = data.get("tag_name", "")
        if not tag.startswith("v"):
            raise ManagerError(f"unexpected latest release tag {tag!r}")
        return tag[1:]
