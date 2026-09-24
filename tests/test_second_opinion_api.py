"""
Unit & Integration tests for FastAPI GET /api/second-opinion endpoint.
All external SerpApi calls are mocked offline.
"""
import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.serpapi.client import SerpApiException


class TestSecondOpinionAPI(unittest.TestCase):
    """Test suite for GET /api/second-opinion endpoint."""

    def setUp(self):
        # Create a clean temporary SQLite database for tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)

        # Patch DB_PATH
        self.db_patcher = patch("app.db.DB_PATH", self.db_path)
        self.db_patcher.start()

        from app.db import init_db
        init_db()

        import numpy as np

        # Insert sample rows for HYD-DEL and HYD-GOI
        conn = sqlite3.connect(self.db_path)
        rows = []
        # HYD-DEL baseline data (692 observations: P25=8288.0, Median=8559.0, P75=10162.0)
        hyd_del_prices = (
            list(np.linspace(7000, 8288, 173)) +
            list(np.linspace(8288, 8559, 173)) +
            list(np.linspace(8559, 10162, 173)) +
            list(np.linspace(10162, 12000, 173))
        )
        for p in hyd_del_prices:
            rows.append(("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", float(p), "2026-09-29", "2026-09-01 10:00:00", "Economy", "0 stops", "06:00", "08:30", "5", "ONE_WAY", "VALID"))

        # HYD-GOI baseline data (168 observations: P25=5359.0, Median=6712.0, P75=8433.0)
        hyd_goi_prices = (
            list(np.linspace(4000, 5359, 42)) +
            list(np.linspace(5359, 6712, 42)) +
            list(np.linspace(6712, 8433, 42)) +
            list(np.linspace(8433, 10000, 42))
        )
        for p in hyd_goi_prices:
            rows.append(("HYD-GOI", "HYD", "GOI", "IndiGo", "Playwright Scraper", float(p), "2026-09-29", "2026-09-01 10:00:00", "Economy", "0 stops", "07:00", "08:30", "4", "ONE_WAY", "VALID"))

        conn.executemany("""
            INSERT INTO raw_prices (route, origin, destination, airline, source, price_inr, travel_date, search_timestamp, class, stops, departure_time, arrival_time, seats_left, fare_type, domestic_eligibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        conn.close()

        from app.main import app
        from app.index_engine import rebuild_route_indices
        rebuild_route_indices()
        self.client = TestClient(app)

    def tearDown(self):
        self.db_patcher.stop()
        try:
            self.temp_db.close()
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_1_successful_hyd_del_request(self, mock_search, mock_cache_set, mock_cache_get):
        """
        Test 1: Successful HYD-DEL request.
        Fixture:
        Live Price: ₹7,542
        FareIndex Baseline: P25=₹8,288, Median=₹8,559, P75=₹10,162
        Google Insights: price_level='high', typical_price_range=[6400, 7500]
        Expected:
        FareIndex Tier = LOW, Google Range Tier = HIGH, Status = FULL_DIVERGENCE, Signal Gap ~ -20.4%
        """
        mock_search.return_value = {
            "search_parameters": {"engine": "google_flights", "departure_id": "HYD", "arrival_id": "DEL", "api_key": "SECRET"},
            "price_insights": {
                "lowest_price": 7542,
                "price_level": "high",
                "typical_price_range": [6400, 7500],
                "price_history": [[1726000000, 7542], [1726086400, 7542]],
            },
            "best_flights": [
                {
                    "price": 7542,
                    "flights": [
                        {
                            "departure_airport": {"id": "HYD", "name": "Rajiv Gandhi International Airport"},
                            "arrival_airport": {"id": "DEL", "name": "Indira Gandhi International Airport"},
                            "airline": "IndiGo",
                        }
                    ]
                },
                {
                    "price": 8550,
                    "flights": [
                        {
                            "departure_airport": {"id": "HYD", "name": "Rajiv Gandhi International Airport"},
                            "arrival_airport": {"id": "DEL", "name": "Indira Gandhi International Airport"},
                            "airline": "Air India",
                        }
                    ]
                }
            ],
            "other_flights": [
                {
                    "price": 9200,
                    "flights": [
                        {
                            "departure_airport": {"id": "HYD", "name": "Rajiv Gandhi International Airport"},
                            "arrival_airport": {"id": "DEL", "name": "Indira Gandhi International Airport"},
                            "airline": "Akasa Air",
                        }
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["route"], "HYD-DEL")
        self.assertEqual(data["origin"], "HYD")
        self.assertEqual(data["destination"], "DEL")
        self.assertEqual(data["outbound_date"], "2026-09-29")
        self.assertEqual(data["live_price"], 7542.0)

        # FareIndex
        self.assertEqual(data["fareindex"]["tier"], "LOW")
        self.assertAlmostEqual(data["fareindex"]["median"], 8559.0, delta=100.0)
        self.assertEqual(data["fareindex"]["observation_count"], 692)

        # Google
        self.assertEqual(data["google"]["lowest_price"], 7542)
        self.assertEqual(data["google"]["price_level"], "high")
        self.assertEqual(data["google"]["range_tier"], "HIGH")
        self.assertEqual(data["google"]["typical_price_range"], {"low": 6400.0, "high": 7500.0})
        self.assertEqual(data["google"]["flight_result_count"], 3)
        self.assertEqual(sorted(data["google"]["airlines"]), ["Air India", "Akasa Air", "IndiGo"])

        # Comparison
        self.assertEqual(data["comparison"]["status"], "FULL_DIVERGENCE")
        self.assertTrue(data["comparison"]["raw_level_disagreement"])
        self.assertAlmostEqual(data["comparison"]["signal_gap"], -20.4, delta=1.0)

        # Explanation & Provenance
        self.assertIn("The two signals use different reference datasets and methodologies", data["explanation"])
        self.assertEqual(data["provenance"]["live_source"], "SerpApi / Google Flights")
        self.assertEqual(data["provenance"]["historical_source"], "FareIndex India")

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_2_successful_hyd_goi_request(self, mock_search, mock_cache_set, mock_cache_get):
        """Test 2: Successful HYD-GOI request."""
        mock_search.return_value = {
            "price_insights": {
                "lowest_price": 3994,
                "price_level": "typical",
                "typical_price_range": [3450, 6200],
            },
            "best_flights": [
                {
                    "price": 3994,
                    "flights": [
                        {
                            "departure_airport": {"id": "HYD"},
                            "arrival_airport": {"id": "GOI"},
                            "airline": "IndiGo",
                        }
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=GOI&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["route"], "HYD-GOI")
        self.assertEqual(data["live_price"], 3994.0)
        self.assertEqual(data["fareindex"]["tier"], "LOW")
        self.assertEqual(data["google"]["range_tier"], "TYPICAL")
        self.assertEqual(data["comparison"]["status"], "PARTIAL_DIVERGENCE")

    def test_3_query_parameter_validation(self):
        """Test 3: Parameter validation for origin, destination, and outbound_date."""
        # Invalid origin length / format
        res = self.client.get("/api/second-opinion?origin=HYDD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 422)

        res = self.client.get("/api/second-opinion?origin=12&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 422)

        # Invalid destination
        res = self.client.get("/api/second-opinion?origin=HYD&destination=D&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 422)

        # Missing parameters
        res = self.client.get("/api/second-opinion?origin=HYD&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 422)

        # Invalid date pattern
        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026/09/29")
        self.assertEqual(res.status_code, 422)

        # Non-existent calendar date (e.g. Feb 30)
        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-02-30")
        self.assertEqual(res.status_code, 422)

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_4_serpapi_http_error(self, mock_search, mock_cache_get):
        """Test 4: SerpApi HTTP error handling and sanitization."""
        mock_search.side_effect = SerpApiException("SerpApi request failed with HTTP 429: Rate limit exceeded", status_code=429)

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 429)
        self.assertIn("Rate limit exceeded", res.json()["detail"])

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_5_missing_price_insights(self, mock_search, mock_cache_set, mock_cache_get):
        """Test 5: Missing price_insights object from SerpApi."""
        mock_search.return_value = {
            # No price_insights
            "best_flights": [
                {
                    "price": 6500,
                    "flights": [
                        {"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "DEL"}, "airline": "IndiGo"}
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["live_price"], 6500.0)
        self.assertIsNone(data["google"]["lowest_price"])
        self.assertIsNone(data["google"]["price_level"])
        self.assertIsNone(data["google"]["typical_price_range"])
        self.assertEqual(data["google"]["range_tier"], "UNKNOWN")
        self.assertEqual(data["comparison"]["status"], "INSUFFICIENT_DATA")

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_6_missing_typical_price_range(self, mock_search, mock_cache_set, mock_cache_get):
        """Test 6: Missing typical_price_range in price_insights."""
        mock_search.return_value = {
            "price_insights": {
                "lowest_price": 7200,
                "price_level": "typical",
                # typical_price_range missing
            },
            "best_flights": [
                {
                    "price": 7200,
                    "flights": [
                        {"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "DEL"}, "airline": "IndiGo"}
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIsNone(data["google"]["typical_price_range"])
        self.assertEqual(data["google"]["range_tier"], "UNKNOWN")
        self.assertEqual(data["comparison"]["status"], "INSUFFICIENT_DATA")

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_7_missing_price_history(self, mock_search, mock_cache_set, mock_cache_get):
        """Test 7: Missing price_history."""
        mock_search.return_value = {
            "price_insights": {
                "lowest_price": 7542,
                "price_level": "high",
                "typical_price_range": [6400, 7500],
                # price_history is None
            },
            "best_flights": [
                {
                    "price": 7542,
                    "flights": [
                        {"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "DEL"}, "airline": "IndiGo"}
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIsNone(data["google"]["price_history"])
        self.assertEqual(data["comparison"]["status"], "FULL_DIVERGENCE")

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_8_international_transit_itinerary_exclusion(self, mock_search, mock_cache_set, mock_cache_get):
        """
        Test 8: International transit itinerary exclusion.
        Returns:
        1. Gulf Air HYD -> BAH -> DEL for ₹4,500 (international transit via Bahrain)
        2. Air India HYD -> DEL for ₹7,542 (domestic)
        Expected:
        live_price must be ₹7,542, ignoring the ₹4,500 international flight.
        """
        mock_search.return_value = {
            "price_insights": {
                "lowest_price": 4500,
                "price_level": "low",
                "typical_price_range": [6400, 7500],
            },
            "best_flights": [
                {
                    "price": 4500,
                    "flights": [
                        {"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "BAH"}, "airline": "Gulf Air"},
                        {"departure_airport": {"id": "BAH"}, "arrival_airport": {"id": "DEL"}, "airline": "Gulf Air"},
                    ]
                },
                {
                    "price": 7542,
                    "flights": [
                        {"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "DEL"}, "airline": "Air India"}
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["live_price"], 7542.0)
        self.assertEqual(data["fareindex"]["tier"], "LOW")

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_9_no_comparable_domestic_itinerary(self, mock_search, mock_cache_set, mock_cache_get):
        """Test 9: All returned itineraries are international transits -> 422 error."""
        mock_search.return_value = {
            "best_flights": [
                {
                    "price": 4500,
                    "flights": [
                        {"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "BAH"}, "airline": "Gulf Air"},
                        {"departure_airport": {"id": "BAH"}, "arrival_airport": {"id": "DEL"}, "airline": "Gulf Air"},
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 422)
        self.assertIn("No comparable domestic itinerary found", res.json()["detail"])

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_10_fareindex_baseline_unavailable(self, mock_search, mock_cache_set, mock_cache_get):
        """Test 10: FareIndex baseline unavailable for unobserved route -> graceful UNKNOWN."""
        mock_search.return_value = {
            "price_insights": {
                "lowest_price": 6000,
                "price_level": "typical",
                "typical_price_range": [5000, 7000],
            },
            "best_flights": [
                {
                    "price": 6000,
                    "flights": [
                        {"departure_airport": {"id": "IXZ"}, "arrival_airport": {"id": "DEL"}, "airline": "IndiGo"}
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=IXZ&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["fareindex"]["tier"], "UNKNOWN")
        self.assertIsNone(data["fareindex"]["p25"])
        self.assertIsNone(data["fareindex"]["median"])
        self.assertIsNone(data["fareindex"]["p75"])
        self.assertEqual(data["fareindex"]["observation_count"], 0)
        self.assertEqual(data["comparison"]["status"], "INSUFFICIENT_DATA")

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_11_correct_response_structure(self, mock_search, mock_cache_set, mock_cache_get):
        """Test 11: Validates exact JSON schema and key structures."""
        mock_search.return_value = {
            "price_insights": {
                "lowest_price": 7542,
                "price_level": "high",
                "typical_price_range": [6400, 7500],
                "price_history": [[1726000000, 7542]],
            },
            "best_flights": [
                {
                    "price": 7542,
                    "flights": [
                        {"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "DEL"}, "airline": "IndiGo"}
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        required_keys = [
            "route", "origin", "destination", "outbound_date", "live_price",
            "fareindex", "google", "comparison", "explanation", "methodology", "provenance"
        ]
        for key in required_keys:
            self.assertIn(key, data)

        fareindex_keys = ["p25", "median", "p75", "tier", "observation_count"]
        for key in fareindex_keys:
            self.assertIn(key, data["fareindex"])

        google_keys = ["lowest_price", "price_level", "typical_price_range", "range_tier", "price_history", "flight_result_count", "airlines"]
        for key in google_keys:
            self.assertIn(key, data["google"])

        comparison_keys = ["status", "signal_gap", "raw_level_disagreement"]
        for key in comparison_keys:
            self.assertIn(key, data["comparison"])

        methodology_keys = ["fareindex_basis", "comparison_type"]
        for key in methodology_keys:
            self.assertIn(key, data["methodology"])

        provenance_keys = ["live_source", "historical_source"]
        for key in provenance_keys:
            self.assertIn(key, data["provenance"])

    @patch("app.serpapi.cache.SerpApiCache.get", return_value=None)
    @patch("app.serpapi.cache.SerpApiCache.set")
    @patch("app.serpapi.client.SerpApiClient.search_flights")
    def test_12_api_key_never_appears_in_response(self, mock_search, mock_cache_set, mock_cache_get):
        """Test 12: Asserts API key is never leaked in the response."""
        mock_search.return_value = {
            "search_parameters": {
                "engine": "google_flights",
                "api_key": "LEAKED_SECRET_KEY_12345XYZ",
                "departure_id": "HYD",
                "arrival_id": "DEL"
            },
            "price_insights": {
                "lowest_price": 7542,
                "price_level": "high",
                "typical_price_range": [6400, 7500],
            },
            "best_flights": [
                {
                    "price": 7542,
                    "flights": [
                        {"departure_airport": {"id": "HYD"}, "arrival_airport": {"id": "DEL"}, "airline": "IndiGo"}
                    ]
                }
            ]
        }

        res = self.client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("LEAKED_SECRET_KEY_12345XYZ", res.text)

    def test_13_existing_endpoints_continue_working(self):
        """Test 13: Regression test verifying existing FareIndex endpoints function without disruption."""
        res_health = self.client.get("/api/health")
        self.assertEqual(res_health.status_code, 200)

        res_routes = self.client.get("/api/routes")
        self.assertEqual(res_routes.status_code, 200)
        self.assertIn("HYD-DEL", res_routes.json())

        res_latest = self.client.get("/api/prices/latest?route=HYD-DEL")
        self.assertEqual(res_latest.status_code, 200)

        res_national = self.client.get("/api/index/national")
        self.assertEqual(res_national.status_code, 200)


if __name__ == "__main__":
    unittest.main()
