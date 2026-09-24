"""
FareIndex India — SerpApi Google Flights Client
Handles secure, authenticated retrieval of Google Flights data via SerpApi.
"""
from __future__ import annotations

import os
import re
import logging
from typing import Any, Optional
import httpx

from ..config import SERPAPI_API_KEY

logger = logging.getLogger("fareindex.serpapi")

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
DEFAULT_TIMEOUT_SECONDS = 30.0


class SerpApiException(Exception):
    """Application-level exception for SerpApi errors, sanitizing sensitive information."""

    def __init__(self, message: str, status_code: Optional[int] = None, error_details: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_details = error_details


def sanitize_message(msg: str, api_key: str = "") -> str:
    """Removes API key strings from any log, URL, or error trace."""
    if not msg:
        return ""
    clean = str(msg)
    if api_key and api_key in clean:
        clean = clean.replace(api_key, "[REDACTED_API_KEY]")
    # Also catch generic api_key query parameters
    clean = re.sub(r"api_key=[^&\s'\"`]+", "api_key=[REDACTED_API_KEY]", clean)
    return clean


class SerpApiClient:
    """
    Client for querying Google Flights via SerpApi.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Optional[httpx.Client] = None,
    ):
        self._api_key = (api_key if api_key is not None else SERPAPI_API_KEY or os.getenv("SERPAPI_API_KEY", "")).strip()
        self._timeout = timeout
        self._client = client

    @property
    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is present."""
        return bool(self._api_key)

    def search_flights(
        self,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        flight_type: int = 2,  # 1 = Round trip, 2 = One way
        currency: str = "INR",
        hl: str = "en",
        gl: str = "in",
        extra_params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Executes a Google Flights search via SerpApi and returns parsed JSON.
        Raises SerpApiException on non-200 or missing API key.
        """
        if not self._api_key:
            raise SerpApiException(
                "SERPAPI_API_KEY is missing or not configured in environment.",
                status_code=401,
                error_details="MISSING_API_KEY",
            )

        params: dict[str, Any] = {
            "engine": "google_flights",
            "departure_id": str(departure_id).strip().upper(),
            "arrival_id": str(arrival_id).strip().upper(),
            "outbound_date": str(outbound_date).strip(),
            "type": int(flight_type),
            "currency": str(currency).strip().upper(),
            "hl": str(hl).strip().lower(),
            "gl": str(gl).strip().lower(),
            "api_key": self._api_key,
        }

        if extra_params:
            for k, v in extra_params.items():
                if k != "api_key":
                    params[k] = v

        try:
            if self._client is not None:
                resp = self._client.get(SERPAPI_ENDPOINT, params=params, timeout=self._timeout)
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.get(SERPAPI_ENDPOINT, params=params)

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # Sanitize returned search_parameters if SerpApi echoes api_key
                    if isinstance(data, dict) and "search_parameters" in data:
                        if isinstance(data["search_parameters"], dict) and "api_key" in data["search_parameters"]:
                            data["search_parameters"]["api_key"] = "[REDACTED_API_KEY]"
                    return data
                except Exception as json_err:
                    raise SerpApiException(
                        f"Failed to parse SerpApi JSON response: {json_err}",
                        status_code=200,
                        error_details=str(json_err),
                    ) from json_err

            # Handle non-200 response
            sanitized_body = sanitize_message(resp.text[:500], self._api_key)
            try:
                err_json = resp.json()
                clean_err_msg = sanitize_message(err_json.get("error", sanitized_body), self._api_key)
            except Exception:
                clean_err_msg = sanitized_body

            raise SerpApiException(
                f"SerpApi request failed with HTTP {resp.status_code}: {clean_err_msg}",
                status_code=resp.status_code,
                error_details=clean_err_msg,
            )

        except SerpApiException:
            raise
        except Exception as exc:
            clean_err = sanitize_message(str(exc), self._api_key)
            raise SerpApiException(
                f"SerpApi connection error: {clean_err}",
                status_code=None,
                error_details=clean_err,
            ) from None
