import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        # Create a clean temporary SQLite database for tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)

        # Patch DB_PATH
        self.db_patcher = patch("app.db.DB_PATH", self.db_path)
        self.db_patcher.start()

        from app.db import init_db
        init_db()

        # Insert sample rows (2 batches: 2026-09-01 and 2026-09-02) with fare_type='ONE_WAY' and domestic_eligibility='VALID'
        conn = sqlite3.connect(self.db_path)
        rows = [
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 7200.0, "2026-09-15", "2026-09-01 10:00:00", "Economy", "0 stops", "06:00", "08:30", "5", "ONE_WAY", "VALID"),
            ("HYD-DEL", "HYD", "DEL", "Air India", "Playwright Scraper", 8500.0, "2026-09-15", "2026-09-01 10:00:00", "Economy", "0 stops", "09:00", "11:30", "2", "ONE_WAY", "VALID"),
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 8000.0, "2026-09-15", "2026-09-02 10:00:00", "Economy", "0 stops", "06:00", "08:30", "3", "ONE_WAY", "VALID"),
            ("HYD-DEL", "HYD", "DEL", "Air India", "Playwright Scraper", 9200.0, "2026-09-15", "2026-09-02 10:00:00", "Economy", "0 stops", "09:00", "11:30", "1", "ONE_WAY", "VALID"),
        ]
        conn.executemany("""
            INSERT INTO raw_prices (route, origin, destination, airline, source, price_inr, travel_date, search_timestamp, class, stops, departure_time, arrival_time, seats_left, fare_type, domestic_eligibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        conn.close()

        # Initialize test client
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

    def test_root(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["project"], "FareIndex India")
        self.assertEqual(data["index_base"], 100.0)

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["service"], "FareIndex India Backend")

    def test_get_routes(self):
        res = self.client.get("/api/routes")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), ["HYD-DEL"])

    def test_get_routes_summary(self):
        res = self.client.get("/api/routes/summary")
        self.assertEqual(res.status_code, 200)
        summaries = res.json()
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["route"], "HYD-DEL")
        self.assertEqual(summaries[0]["observation_count"], 4)
        self.assertIsNotNone(summaries[0]["latest_index"])
        self.assertIsNotNone(summaries[0]["previous_index"])
        self.assertIsNotNone(summaries[0]["index_change"])

    def test_get_routes_summary_specific_route(self):
        res = self.client.get("/api/routes/summary?route=HYD-DEL")
        self.assertEqual(res.status_code, 200)
        summaries = res.json()
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["route"], "HYD-DEL")

    def test_get_routes_summary_non_existent_route(self):
        res = self.client.get("/api/routes/summary?route=NON-EXISTENT")
        self.assertEqual(res.status_code, 404)

    def test_get_national_index(self):
        res = self.client.get("/api/index/national")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("FareIndex India", data["index_name"])
        self.assertIn("values", data)
        self.assertEqual(len(data["values"]), 2)
        self.assertIsNotNone(data["latest_value"])

    def test_get_route_index(self):
        res = self.client.get("/api/index/route/HYD-DEL")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["route"], "HYD-DEL")
        self.assertEqual(len(data["values"]), 2)

    def test_get_route_index_404(self):
        res = self.client.get("/api/index/route/BOM-GOI")
        self.assertEqual(res.status_code, 404)

    def test_get_booking_curve(self):
        res = self.client.get("/api/analytics/booking-curve?route=HYD-DEL")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["route"], "HYD-DEL")
        self.assertEqual(data["total_observations"], 4)
        self.assertEqual(data["usable_observations"], 4)
        self.assertEqual(len(data["curve"]), 2)

    def test_get_airline_analytics(self):
        res = self.client.get("/api/analytics/airlines?route=HYD-DEL")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["route"], "HYD-DEL")
        self.assertEqual(data["total_observations"], 4)
        self.assertEqual(len(data["airlines"]), 2)

    def test_get_latest_prices_provenance(self):
        res = self.client.get("/api/prices/latest?route=HYD-DEL")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["route"], "HYD-DEL")
        self.assertEqual(len(data["fares"]), 2)
        for fare in data["fares"]:
            self.assertIn("provenance", fare)
            self.assertIn("source", fare)

    def test_rebuild_index_admin(self):
        res = self.client.post("/api/admin/rebuild-index")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("rows_written", data)
        self.assertEqual(data["routes"], 1)

    def test_scrape_status(self):
        res = self.client.get("/api/admin/scrape-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)

if __name__ == "__main__":
    unittest.main()
