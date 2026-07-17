"""Polite HTTP layer: rate limiting, retries, disk cache, abort on bot-block."""

import hashlib
import json
import random
import time
from pathlib import Path

import requests

from .db import REPO_ROOT

CACHE_DIR = REPO_ROOT / "data" / "cache"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class BotBlocked(Exception):
    """Source returned 403/challenge — stop this source's run, don't hammer."""


class PoliteSession:
    def __init__(self, source_code: str, min_delay: float = 2.0, max_delay: float = 5.0,
                 cache_ttl_s: int = 6 * 3600):
        self.source_code = source_code
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.cache_ttl_s = cache_ttl_s
        self.cache_dir = CACHE_DIR / source_code
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        })
        self._last_request_at = 0.0

    def _cache_path(self, url: str, params) -> Path:
        key = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request_at
        wait = random.uniform(self.min_delay, self.max_delay) - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def get(self, url: str, params: dict | None = None, ttl_s: int | None = None) -> str:
        """GET with disk cache. Returns response body text."""
        ttl = self.cache_ttl_s if ttl_s is None else ttl_s
        cache = self._cache_path(url, params)
        if cache.exists() and (time.time() - cache.stat().st_mtime) < ttl:
            return cache.read_text()

        last_err = None
        for attempt in range(3):
            self._throttle()
            try:
                resp = self.session.get(url, params=params, timeout=30)
            except requests.RequestException as e:
                last_err = e
                time.sleep(2 ** attempt * 3)
                continue
            if resp.status_code in (403, 429):
                raise BotBlocked(f"{self.source_code}: HTTP {resp.status_code} on {url}")
            if resp.status_code >= 500:
                last_err = RuntimeError(f"HTTP {resp.status_code}")
                time.sleep(2 ** attempt * 3)
                continue
            resp.raise_for_status()
            cache.write_text(resp.text)
            return resp.text
        raise RuntimeError(f"{self.source_code}: giving up on {url}: {last_err}")

    def get_json(self, url: str, params: dict | None = None, ttl_s: int | None = None):
        return json.loads(self.get(url, params, ttl_s))
