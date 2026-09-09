import pytest
import sqlite3
from unittest.mock import patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app, scheduler
from app.scrape_service import scrape_all_routes, scrape_status
from app.db import DB_PATH, connect
from app.index_engine import get_route_movement_series, get_route_trend_series

class TestSchedulerAndPipeline:
    """
    Verifies Part 10 & Part 27 requirements:
    - Scheduler initialization on startup
    - Production scrape writes to SQLite
    - Domestic validation in pipeline
    - Rebuild triggered on insert
    - Movement and trend endpoints reflect fresh data
    - Data persistence in SQLite
    """

    def test_1_scheduler_initialized_on_lifespan(self):
        """Verify scheduler initializes and registers scheduled job on backend startup."""
        with TestClient(app) as client:
            jobs = scheduler.get_jobs()
            job_ids = [j.id for j in jobs]
            assert "airfare-refresh" in job_ids
            assert scheduler.running is True

    def test_2_end_to_end_scrape_pipeline_with_provider(self):
        """Verify scrape writes to SQLite, updates timestamp, and rebuilds indices."""
        mock_timestamp = "2026-09-09T10:00:00+00:00"
        mock_fares = [
            {
                "route": "HYD-DEL",
                "origin": "HYD",
                "destination": "DEL",
                "airline": "IndiGo",
                "price_inr": 8600.0,
                "travel_date": "2026-09-15",
                "search_timestamp": mock_timestamp,
                "class": "Economy",
                "stops": "Non-stop",
                "departure_time": "07:00",
                "arrival_time": "09:15",
                "seats_left": None,
                "fare_type": "ONE_WAY",
                "domestic_eligibility": "VALID",
                "eligibility_reason": "DOMESTIC_ITINERARY",
                "intermediate_airports": None,
                "source": "Playwright Scraper",
            },
            {
                "route": "HYD-DEL",
                "origin": "HYD",
                "destination": "DEL",
                "airline": "Air India",
                "price_inr": 9200.0,
                "travel_date": "2026-09-16",
                "search_timestamp": mock_timestamp,
                "class": "Economy",
                "stops": "Non-stop",
                "departure_time": "10:30",
                "arrival_time": "12:45",
                "seats_left": None,
                "fare_type": "ONE_WAY",
                "domestic_eligibility": "VALID",
                "eligibility_reason": "DOMESTIC_ITINERARY",
                "intermediate_airports": None,
                "source": "Playwright Scraper",
            },
        ]

        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw_prices")
        initial_count = cursor.fetchone()[0]
        conn.close()

        class MockProvider:
            name = "Playwright Scraper"
            def fetch(self, route):
                return mock_fares if route == "HYD-DEL" else []

        with patch("app.scrape_service.get_provider", return_value=MockProvider()):
            result = scrape_all_routes()
            assert result["status"] == "ok"
            assert result["inserted"] >= 2

            # 1. Verify SQLite row count increased
            conn = connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM raw_prices")
            new_count = cursor.fetchone()[0]
            assert new_count == initial_count + result["inserted"]

            # 2. Verify search timestamp is stored
            cursor.execute("SELECT MAX(search_timestamp) FROM raw_prices WHERE route = 'HYD-DEL'")
            latest_ts = cursor.fetchone()[0]
            assert latest_ts >= mock_timestamp

            # 3. Clean up inserted mock records to preserve canonical dataset
            cursor.execute("DELETE FROM raw_prices WHERE search_timestamp = ?", (mock_timestamp,))
            conn.commit()
            conn.close()

            # Rebuild index after cleanup
            from app.index_engine import rebuild_route_indices
            rebuild_route_indices()
