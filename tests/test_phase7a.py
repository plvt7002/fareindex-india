import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.db import init_db
from app.scrape_service import validate_observation
from app.index_engine import get_public_snapshot_dataframe, rebuild_route_indices

class TestPhase7AFareTypeAndValidation(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)
        self.db_patcher = patch("app.db.DB_PATH", self.db_path)
        self.db_patcher.start()
        init_db()

    def tearDown(self):
        self.db_patcher.stop()
        try:
            self.temp_db.close()
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_schema_has_fare_type_column_and_index(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(raw_prices)")
        cols = [row[1] for row in cursor.fetchall()]
        self.assertIn("fare_type", cols)

        cursor.execute("PRAGMA index_list(raw_prices)")
        indices = [row[1] for row in cursor.fetchall()]
        self.assertIn("idx_raw_fare_type", indices)
        conn.close()

    def test_validate_observation_rules(self):
        # Valid ONE_WAY live observation
        valid_row = {
            "source": "Playwright Scraper",
            "price_inr": 8500.0,
            "class": "Economy",
            "fare_type": "ONE_WAY",
            "trip_type": "one_way",
            "passenger_count": 1,
            "currency": "INR",
            "domestic_eligibility": "VALID",
            "eligibility_reason": "DOMESTIC_ITINERARY",
        }
        ok, msg = validate_observation(valid_row)
        self.assertTrue(ok, msg)

        # Rejects legacy round trip
        rt_row = dict(valid_row, fare_type="ROUND_TRIP_LEGACY")
        ok, _ = validate_observation(rt_row)
        self.assertFalse(ok)

        # Rejects non-economy
        biz_row = dict(valid_row, **{"class": "Business"})
        ok, _ = validate_observation(biz_row)
        self.assertFalse(ok)

        # Rejects non-INR
        usd_row = dict(valid_row, currency="USD")
        ok, _ = validate_observation(usd_row)
        self.assertFalse(ok)

        # Rejects multi-passenger
        pass_row = dict(valid_row, passenger_count=2)
        ok, _ = validate_observation(pass_row)
        self.assertFalse(ok)

        # Rejects invalid price
        zero_row = dict(valid_row, price_inr=0)
        ok, _ = validate_observation(zero_row)
        self.assertFalse(ok)

    def test_legacy_round_trip_excluded_from_public_index(self):
        conn = sqlite3.connect(self.db_path)
        # Insert 1 legacy round trip observation and 1 fresh ONE_WAY observation
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 18400.0, '2026-09-15', '2026-09-08T14:15:00Z', 'Economy', 'Nonstop', 'ROUND_TRIP_LEGACY', 'INVALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 9200.0, '2026-09-15', '2026-09-08T15:15:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'DemoProvider', 5000.0, '2026-09-15', '2026-09-08T15:15:00Z', 'Economy', 'Nonstop', 'UNKNOWN', 'UNKNOWN')
        """)
        conn.commit()
        conn.close()

        # Check public snapshot dataframe
        conn = sqlite3.connect(self.db_path)
        df = get_public_snapshot_dataframe(conn, "HYD-DEL")
        conn.close()
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["price_inr"], 9200.0)
        self.assertEqual(df.iloc[0]["fare_type"], "ONE_WAY")

        # Check routes summary
        from app.index_engine import get_routes_summary
        summaries = get_routes_summary("HYD-DEL")
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["observation_count"], 1)
        self.assertEqual(summaries[0]["latest_avg_fare"], 9200.0)
        self.assertEqual(summaries[0]["all_time_min_fare"], 9200.0)
        self.assertEqual(summaries[0]["all_time_max_fare"], 9200.0)

if __name__ == "__main__":
    unittest.main()
