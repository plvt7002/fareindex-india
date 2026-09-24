"""
FareIndex India — SerpApi Response Local Cache
Provides persistent file-based caching for Google Flights queries during development and validation.
Never persists sensitive API credentials.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from ..config import BASE_DIR

logger = logging.getLogger("fareindex.serpapi.cache")

DEFAULT_CACHE_DIR = BASE_DIR / "data" / "serpapi_cache"


class SerpApiCache:
    """
    File-based JSON cache for SerpApi Google Flights responses.
    """

    def __init__(self, cache_dir: Optional[Path | str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_filename(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        currency: str = "INR",
        flight_type: int = 2,
        hl: str = "en",
        gl: str = "in",
    ) -> str:
        """Generates a predictable, filesystem-safe cache file name."""
        orig = str(origin).strip().upper()
        dest = str(destination).strip().upper()
        date_str = str(outbound_date).strip()
        curr = str(currency).strip().upper()
        return f"flights_{orig}_{dest}_{date_str}_{curr}_t{flight_type}_{hl}_{gl}.json"

    def get_path(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        currency: str = "INR",
        flight_type: int = 2,
        hl: str = "en",
        gl: str = "in",
    ) -> Path:
        """Returns the full Path to the cache file."""
        fname = self._get_filename(origin, destination, outbound_date, currency, flight_type, hl, gl)
        return self.cache_dir / fname

    def has(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        currency: str = "INR",
        flight_type: int = 2,
        hl: str = "en",
        gl: str = "in",
    ) -> bool:
        """Checks if a valid cache entry exists."""
        p = self.get_path(origin, destination, outbound_date, currency, flight_type, hl, gl)
        return p.is_file()

    def get(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        currency: str = "INR",
        flight_type: int = 2,
        hl: str = "en",
        gl: str = "in",
    ) -> Optional[dict[str, Any]]:
        """
        Retrieves cached response JSON if present.
        Returns None if cache miss or corrupted.
        """
        path = self.get_path(origin, destination, outbound_date, currency, flight_type, hl, gl)
        if not path.is_file():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
            return None
        except Exception as exc:
            logger.warning("Failed to read SerpApi cache file %s: %s", path, exc)
            return None

    def set(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        data: dict[str, Any],
        currency: str = "INR",
        flight_type: int = 2,
        hl: str = "en",
        gl: str = "in",
    ) -> Path:
        """
        Stores response JSON to cache after stripping any API keys.
        Returns the saved file Path.
        """
        path = self.get_path(origin, destination, outbound_date, currency, flight_type, hl, gl)
        
        # Deep-copy / sanitize data before persisting
        data_to_store = dict(data)
        if "search_parameters" in data_to_store and isinstance(data_to_store["search_parameters"], dict):
            sp = dict(data_to_store["search_parameters"])
            if "api_key" in sp:
                sp["api_key"] = "[REDACTED_API_KEY]"
            data_to_store["search_parameters"] = sp

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data_to_store, f, indent=2, ensure_ascii=False)

        return path

    def clear(self) -> int:
        """Deletes all JSON files in the cache directory and returns count of files removed."""
        count = 0
        if self.cache_dir.is_dir():
            for p in self.cache_dir.glob("*.json"):
                try:
                    p.unlink()
                    count += 1
                except Exception:
                    pass
        return count
