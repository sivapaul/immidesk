import os
import time
from pathlib import Path

import requests

USER_AGENT = os.environ.get(
    "IMMIDESK_USER_AGENT",
    "ImmiDesk/0.1 (open-source immigration dashboard; +https://github.com/immidesk/immidesk)",
)


class FetchError(RuntimeError):
    pass


class NoFixture(FetchError):
    pass


class Fetcher:
    """Live HTTP fetcher. Offline mode reads tests/fixtures/<key>.<ext> instead."""

    def __init__(self, fixtures_dir=None, timeout=30, retries=3, delay=1.0):
        self.fixtures = Path(fixtures_dir) if fixtures_dir else None
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"})

    @property
    def offline(self):
        return self.fixtures is not None

    def _fixture(self, key):
        for ext in ("html", "json", "xml", "rss", "txt", "db"):
            p = self.fixtures / f"{key}.{ext}"
            if p.exists():
                return p
        raise NoFixture(f"no fixture for {key}")

    def get(self, url, key, headers=None, params=None, binary=False):
        if self.offline:
            p = self._fixture(key)
            return p.read_bytes() if binary else p.read_text(encoding="utf-8")
        last = None
        for attempt in range(1, self.retries + 1):
            try:
                r = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
                if r.status_code == 200:
                    time.sleep(self.delay)
                    return r.content if binary else r.text
                last = f"HTTP {r.status_code} from {url}"
                if r.status_code in (401, 403, 404):
                    break
            except requests.RequestException as e:
                last = f"{type(e).__name__}: {e}"
            time.sleep(2 ** attempt)
        raise FetchError(last or f"failed to fetch {url}")

    def get_json(self, url, key, headers=None, params=None):
        import json
        return json.loads(self.get(url, key, headers=headers, params=params))
