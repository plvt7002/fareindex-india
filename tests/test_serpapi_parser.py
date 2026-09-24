"""
Unit tests for SerpApi integration layer:
- Client (mocked HTTP, error handling, API key sanitization)
- Parser (robust handling of full, partial, missing price_insights, typical_price_range, price_history)
- Itinerary Validation (domestic vs international transit detection)
- Local Cache (get, set, has, clear, credential sanitization)
"""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import httpx

from app.serpapi.client import SerpApiClient, SerpApiException, sanitize_message
from app.serpapi.parser import (
    parse_google_flights_response,
    parse_flight_item,
    is_domestic_itinerary,
)
from app.serpapi.cache import SerpApiCache


# Mock Fixture 1: Complete response with full price_insights, multiple airlines, and flights
MOCK_FULL_RESPONSE = {
    "search_metadata": {
        "status": "Success",
    },
    "search_parameters": {
        "engine": "google_flights",
        "departure_id": "HYD",
        "arrival_id": "DEL",
        "outbound_date": "2026-09-29",
        "currency": "INR",
        "api_key": "secret_test_key_12345"
    },
    "price_insights": {
        "lowest_price": 7542,
        "price_level": "high",
        "typical_price_range": [6400, 7500],
        "price_history": [
            [1726000000, 7200],
            [1726086400, 7542]
        ]
    },
    "best_flights": [
        {
            "price": 7542,
            "total_duration": 135,
            "type": "One way",
            "flights": [
                {
                    "departure_airport": {"id": "HYD", "name": "Rajiv Gandhi Intl", "time": "2026-09-29 06:00"},
                    "arrival_airport": {"id": "DEL", "name": "Indira Gandhi Intl", "time": "2026-09-29 08:15"},
                    "airline": "IndiGo",
                    "flight_number": "6E 2024",
                    "duration": 135
                }
            ]
        }
    ],
    "other_flights": [
        {
            "price": 8200,
            "total_duration": 140,
            "type": "One way",
            "flights": [
                {
                    "departure_airport": {"id": "HYD", "name": "Rajiv Gandhi Intl", "time": "2026-09-29 09:00"},
                    "arrival_airport": {"id": "DEL", "name": "Indira Gandhi Intl", "time": "2026-09-29 11:20"},
                    "airline": "Air India",
                    "flight_number": "AI 542",
                    "duration": 140
                }
            ]
        },
        {
            "price": 8900,
            "total_duration": 130,
            "type": "One way",
            "flights": [
                {
                    "departure_airport": {"id": "HYD", "name": "Rajiv Gandhi Intl", "time": "2026-09-29 14:00"},
                    "arrival_airport": {"id": "DEL", "name": "Indira Gandhi Intl", "time": "2026-09-29 16:10"},
                    "airline": "Akasa Air",
                    "flight_number": "QP 1102",
                    "duration": 130
                }
            ]
        }
    ]
}

# Mock Fixture 2: Response missing price_insights entirely
MOCK_MISSING_PRICE_INSIGHTS = {
    "search_parameters": {
        "engine": "google_flights",
        "departure_id": "HYD",
        "arrival_id": "DEL",
        "outbound_date": "2026-09-27"
    },
    "best_flights": [
        {
            "price": 7994,
            "flights": [
                {
                    "departure_airport": {"id": "HYD"},
                    "arrival_airport": {"id": "DEL"},
                    "airline": "IndiGo"
                }
            ]
        }
    ],
    "other_flights": []
}

# Mock Fixture 3: Response missing typical_price_range
MOCK_MISSING_TYPICAL_RANGE = {
    "price_insights": {
        "lowest_price": 5200,
        "price_level": "typical",
        # typical_price_range is omitted
        "price_history": [[1726000000, 5200]]
    },
    "best_flights": []
}

# Mock Fixture 4: Response missing price_history
MOCK_MISSING_PRICE_HISTORY = {
    "price_insights": {
        "lowest_price": 4500,
        "price_level": "low",
        "typical_price_range": [4200, 6000]
        # price_history is omitted
    },
    "best_flights": []
}

# Mock Fixture 5: International transit flight (HYD -> Bahrain -> GOI on Gulf Air)
MOCK_INTL_TRANSIT_FLIGHT = {
    "price": 4215,
    "flights": [
        {
            "departure_airport": {"id": "HYD", "name": "Hyderabad"},
            "arrival_airport": {"id": "BAH", "name": "Bahrain International"},
            "airline": "Gulf Air"
        },
        {
            "departure_airport": {"id": "BAH", "name": "Bahrain International"},
            "arrival_airport": {"id": "GOI", "name": "Dabolim Goa"},
            "airline": "Gulf Air"
        }
    ]
}

# Mock Fixture 6: Domestic connecting flight (HYD -> BOM -> GOI on IndiGo)
MOCK_DOMESTIC_CONNECTING_FLIGHT = {
    "price": 5400,
    "flights": [
        {
            "departure_airport": {"id": "HYD", "name": "Hyderabad"},
            "arrival_airport": {"id": "BOM", "name": "Mumbai"},
            "airline": "IndiGo"
        },
        {
            "departure_airport": {"id": "BOM", "name": "Mumbai"},
            "arrival_airport": {"id": "GOI", "name": "Dabolim Goa"},
            "airline": "IndiGo"
        }
    ]
}


class TestSerpApiParser(unittest.TestCase):
    """Unit tests for SerpApi parser and itinerary validation."""

    def test_a_full_price_insights_parsing(self):
        parsed = parse_google_flights_response(MOCK_FULL_RESPONSE)
        self.assertEqual(parsed["lowest_price"], 7542.0)
        self.assertEqual(parsed["price_level"], "high")
        self.assertEqual(parsed["typical_price_range"], {"low": 6400.0, "high": 7500.0})
        self.assertEqual(len(parsed["price_history"]), 2)
        self.assertEqual(parsed["total_flight_results"], 3)
        self.assertEqual(len(parsed["best_flights"]), 1)
        self.assertEqual(len(parsed["other_flights"]), 2)
        self.assertEqual(parsed["airlines"], ["Air India", "Akasa Air", "IndiGo"])
        # Verify search parameters sanitized
        self.assertEqual(parsed["search_parameters"]["api_key"], "[REDACTED_API_KEY]")

    def test_b_missing_price_insights(self):
        parsed = parse_google_flights_response(MOCK_MISSING_PRICE_INSIGHTS)
        self.assertIsNone(parsed["lowest_price"])
        self.assertIsNone(parsed["price_level"])
        self.assertIsNone(parsed["typical_price_range"])
        self.assertIsNone(parsed["price_history"])
        self.assertEqual(parsed["total_flight_results"], 1)
        self.assertEqual(parsed["airlines"], ["IndiGo"])

    def test_c_missing_typical_price_range(self):
        parsed = parse_google_flights_response(MOCK_MISSING_TYPICAL_RANGE)
        self.assertEqual(parsed["lowest_price"], 5200.0)
        self.assertEqual(parsed["price_level"], "typical")
        self.assertIsNone(parsed["typical_price_range"])
        self.assertIsNotNone(parsed["price_history"])

    def test_d_missing_price_history(self):
        parsed = parse_google_flights_response(MOCK_MISSING_PRICE_HISTORY)
        self.assertEqual(parsed["lowest_price"], 4500.0)
        self.assertEqual(parsed["price_level"], "low")
        self.assertEqual(parsed["typical_price_range"], {"low": 4200.0, "high": 6000.0})
        self.assertIsNone(parsed["price_history"])

    def test_e_multiple_airlines_extracted(self):
        parsed = parse_google_flights_response(MOCK_FULL_RESPONSE)
        self.assertIn("IndiGo", parsed["airlines"])
        self.assertIn("Air India", parsed["airlines"])
        self.assertIn("Akasa Air", parsed["airlines"])
        self.assertEqual(len(parsed["airlines"]), 3)

    def test_f_multiple_flight_results(self):
        parsed = parse_google_flights_response(MOCK_FULL_RESPONSE)
        self.assertEqual(len(parsed["all_flights"]), 3)
        self.assertEqual(parsed["all_flights"][0]["price"], 7542.0)
        self.assertEqual(parsed["all_flights"][1]["price"], 8200.0)
        self.assertEqual(parsed["all_flights"][2]["price"], 8900.0)

    def test_g_domestic_itinerary_validation(self):
        # Direct domestic flight
        is_dom, reason, airports = is_domestic_itinerary(MOCK_FULL_RESPONSE["best_flights"][0])
        self.assertTrue(is_dom)
        self.assertEqual(reason, "DOMESTIC_ITINERARY")
        self.assertEqual(airports, ["HYD", "DEL"])

        # Connecting domestic flight (HYD -> BOM -> GOI)
        is_dom_conn, reason_conn, airports_conn = is_domestic_itinerary(MOCK_DOMESTIC_CONNECTING_FLIGHT)
        self.assertTrue(is_dom_conn)
        self.assertEqual(reason_conn, "DOMESTIC_ITINERARY")
        self.assertEqual(airports_conn, ["HYD", "BOM", "GOI"])

    def test_h_international_transit_itinerary_validation(self):
        # International transit (Gulf Air via BAH)
        is_dom, reason, airports = is_domestic_itinerary(MOCK_INTL_TRANSIT_FLIGHT)
        self.assertFalse(is_dom)
        self.assertTrue("FOREIGN_TRANSIT" in reason or "INTERNATIONAL_TRANSIT" in reason)
        self.assertIn("BAH", airports)

    def test_i_malformed_and_partial_responses(self):
        # Empty dict
        empty_res = parse_google_flights_response({})
        self.assertIsNone(empty_res["lowest_price"])
        self.assertEqual(empty_res["total_flight_results"], 0)

        # None input
        none_res = parse_google_flights_response(None)
        self.assertIsNone(none_res["lowest_price"])
        self.assertEqual(none_res["total_flight_results"], 0)

        # Non-numeric prices or malformed ranges
        malformed = {
            "price_insights": {
                "lowest_price": "invalid_number",
                "price_level": "typical",
                "typical_price_range": ["bad", "range"],
                "price_history": "not_a_list"
            },
            "best_flights": [{"price": "invalid"}]
        }
        res = parse_google_flights_response(malformed)
        self.assertIsNone(res["lowest_price"])
        self.assertIsNone(res["typical_price_range"])
        self.assertIsNone(res["price_history"])
        self.assertEqual(res["total_flight_results"], 1)
        self.assertIsNone(res["best_flights"][0]["price"])


class TestSerpApiClient(unittest.TestCase):
    """Unit tests for SerpApiClient and error/security handling."""

    def test_missing_api_key_raises_exception(self):
        client = SerpApiClient(api_key="")
        with self.assertRaises(SerpApiException) as ctx:
            client.search_flights(departure_id="HYD", arrival_id="DEL", outbound_date="2026-09-29")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("SERPAPI_API_KEY is missing", str(ctx.exception))

    def test_sanitize_message_strips_api_keys(self):
        raw_key = "super_secret_test_key_xyz987"
        msg = f"Error connecting to https://serpapi.com/search.json?api_key={raw_key}&engine=google_flights using {raw_key}"
        clean = sanitize_message(msg, api_key=raw_key)
        self.assertNotIn(raw_key, clean)
        self.assertIn("[REDACTED_API_KEY]", clean)

    def test_non_200_http_response_raises_sanitized_exception(self):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = '{"error": "Rate limit exceeded for api_key=secret_12345"}'
        mock_response.json.return_value = {"error": "Rate limit exceeded for api_key=secret_12345"}

        mock_http_client = MagicMock()
        mock_http_client.get.return_value = mock_response

        client = SerpApiClient(api_key="secret_12345", client=mock_http_client)
        with self.assertRaises(SerpApiException) as ctx:
            client.search_flights(departure_id="HYD", arrival_id="DEL", outbound_date="2026-09-29")

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertNotIn("secret_12345", str(ctx.exception))
        self.assertIn("Rate limit exceeded", str(ctx.exception))


class TestSerpApiCache(unittest.TestCase):
    """Unit tests for SerpApi local caching mechanism."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache = SerpApiCache(cache_dir=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cache_set_get_and_sanitization(self):
        test_payload = {
            "search_parameters": {
                "departure_id": "HYD",
                "arrival_id": "DEL",
                "api_key": "raw_secret_key_to_sanitize"
            },
            "price_insights": {"lowest_price": 7500}
        }

        self.assertFalse(self.cache.has("HYD", "DEL", "2026-09-29"))
        self.assertIsNone(self.cache.get("HYD", "DEL", "2026-09-29"))

        saved_path = self.cache.set("HYD", "DEL", "2026-09-29", test_payload)
        self.assertTrue(saved_path.is_file())
        self.assertTrue(self.cache.has("HYD", "DEL", "2026-09-29"))

        cached_data = self.cache.get("HYD", "DEL", "2026-09-29")
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data["price_insights"]["lowest_price"], 7500)
        # Verify key was sanitized upon saving
        self.assertEqual(cached_data["search_parameters"]["api_key"], "[REDACTED_API_KEY]")

        # Test clear
        count = self.cache.clear()
        self.assertEqual(count, 1)
        self.assertFalse(self.cache.has("HYD", "DEL", "2026-09-29"))


if __name__ == "__main__":
    unittest.main()
