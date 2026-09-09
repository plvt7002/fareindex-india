import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.index_engine import (
    rebuild_route_indices,
    get_national_composite_index,
    get_routes_summary,
    get_booking_curve_analytics,
    get_airline_analytics,
    get_public_snapshot_dataframe,
    get_provenance_summary,
)
from app.db import init_db

class TestIndexEngine(unittest.TestCase):
    def setUp(self):
        # Create a clean temporary SQLite database for tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)

        # Patch DB_PATH in db module
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

    def _insert_sample_data(self):
        conn = sqlite3.connect(self.db_path)
        # Insert test data across 2 routes and 2 dates with shared batch search_timestamp per collection run
        rows = [
            # HYD-DEL: Date 1 (2026-09-01 batch) -> Mean: (7000 + 8000) / 2 = 7500
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 7000.0, "2026-09-10", "2026-09-01 10:00:00", "ONE_WAY", "VALID"),
            ("HYD-DEL", "HYD", "DEL", "Air India", "Playwright Scraper", 8000.0, "2026-09-10", "2026-09-01 10:00:00", "ONE_WAY", "VALID"),
            # HYD-DEL: Date 2 (2026-09-02 batch) -> Mean: (9000 + 10000) / 2 = 9500
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 9000.0, "2026-09-10", "2026-09-02 10:00:00", "ONE_WAY", "VALID"),
            ("HYD-DEL", "HYD", "DEL", "Air India", "Playwright Scraper", 10000.0, "2026-09-10", "2026-09-02 10:00:00", "ONE_WAY", "VALID"),
            # DEL-BOM: Date 1 (2026-09-01 batch) -> Mean: 6000
            ("DEL-BOM", "DEL", "BOM", "Akasa Air", "Playwright Scraper", 6000.0, None, "2026-09-01 12:00:00", "ONE_WAY", "VALID"),
            # DEL-BOM: Date 2 (2026-09-02 batch) -> Mean: 8000
            ("DEL-BOM", "DEL", "BOM", "Akasa Air", "Playwright Scraper", 8000.0, "2026-09-16", "2026-09-02 12:00:00", "ONE_WAY", "VALID"),
        ]
        conn.executemany("""
            INSERT INTO raw_prices (route, origin, destination, airline, source, price_inr, travel_date, search_timestamp, fare_type, domestic_eligibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        conn.close()

    def test_rebuild_route_indices(self):
        self._insert_sample_data()
        result = rebuild_route_indices()
        self.assertEqual(result["routes"], 2)
        self.assertEqual(result["rows_written"], 4)

        # Baseline for HYD-DEL = (7500 + 9500) / 2 = 8500
        # Index on 2026-09-01 = (7500 / 8500) * 100 = 88.24
        # Index on 2026-09-02 = (9500 / 8500) * 100 = 111.76
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        hyd_del_indices = conn.execute("""
            SELECT * FROM index_values WHERE route = 'HYD-DEL' ORDER BY observation_date
        """).fetchall()
        conn.close()

        self.assertEqual(len(hyd_del_indices), 2)
        self.assertEqual(hyd_del_indices[0]["observation_date"], "2026-09-01")
        self.assertAlmostEqual(hyd_del_indices[0]["avg_fare"], 7500.0, places=1)
        self.assertAlmostEqual(hyd_del_indices[0]["baseline_fare"], 8500.0, places=1)
        self.assertAlmostEqual(hyd_del_indices[0]["index_value"], 88.24, places=1)

        self.assertEqual(hyd_del_indices[1]["observation_date"], "2026-09-02")
        self.assertAlmostEqual(hyd_del_indices[1]["avg_fare"], 9500.0, places=1)
        self.assertAlmostEqual(hyd_del_indices[1]["index_value"], 111.76, places=1)

    def test_national_composite_index(self):
        self._insert_sample_data()
        rebuild_route_indices()

        with patch("app.index_engine.ROUTE_WEIGHTS", {"HYD-DEL": 1.0, "DEL-BOM": 1.5}):
            nat = get_national_composite_index()
            self.assertEqual(len(nat["values"]), 2)
            self.assertIsNotNone(nat["latest_value"])

            val_01 = nat["values"][0]
            self.assertEqual(val_01["observation_date"], "2026-09-01")
            self.assertEqual(val_01["contributing_routes_count"], 2)

            val_02 = nat["values"][1]
            self.assertIsNotNone(val_02["index_change_from_previous"])
            self.assertIsNotNone(val_02["index_change_pct"])

    def test_routes_summary(self):
        self._insert_sample_data()
        rebuild_route_indices()

        summaries = get_routes_summary()
        self.assertEqual(len(summaries), 2)

        hyd_summary = next(s for s in summaries if s["route"] == "HYD-DEL")
        self.assertEqual(hyd_summary["observation_count"], 4)
        self.assertEqual(hyd_summary["observation_days_count"], 2)
        self.assertEqual(hyd_summary["all_time_min_fare"], 7000.0)
        self.assertEqual(hyd_summary["all_time_max_fare"], 10000.0)
        self.assertEqual(hyd_summary["latest_index"], 111.76)
        self.assertEqual(hyd_summary["previous_index"], 88.24)
        self.assertAlmostEqual(hyd_summary["index_change"], 23.52, places=1)
        self.assertIn("IndiGo", hyd_summary["airlines"])
        self.assertIn("Air India", hyd_summary["airlines"])

    def test_airline_analytics(self):
        self._insert_sample_data()
        air = get_airline_analytics("HYD-DEL")
        self.assertEqual(air["route"], "HYD-DEL")
        self.assertEqual(air["total_observations"], 4)
        self.assertEqual(len(air["airlines"]), 2)

        indigo = next(a for a in air["airlines"] if a["airline"] == "IndiGo")
        self.assertEqual(indigo["observation_count"], 2)
        self.assertEqual(indigo["min_fare"], 7000.0)
        self.assertEqual(indigo["max_fare"], 9000.0)
        self.assertEqual(indigo["spread"], 2000.0)
        self.assertEqual(indigo["avg_fare"], 8000.0)
        self.assertEqual(indigo["market_share_pct"], 50.0)

    def test_booking_curve_with_usable_and_missing_dates(self):
        self._insert_sample_data()
        
        bc = get_booking_curve_analytics("HYD-DEL")
        self.assertEqual(bc["total_observations"], 4)
        self.assertEqual(bc["usable_observations"], 4)
        self.assertEqual(bc["missing_travel_date_count"], 0)
        self.assertEqual(len(bc["curve"]), 2)
        
        lead_days = [c["lead_time_days"] for c in bc["curve"]]
        self.assertEqual(lead_days, [8, 9])

        bc_del_bom = get_booking_curve_analytics("DEL-BOM")
        self.assertEqual(bc_del_bom["total_observations"], 2)
        self.assertEqual(bc_del_bom["usable_observations"], 1)
        self.assertEqual(bc_del_bom["missing_travel_date_count"], 1)
        self.assertEqual(len(bc_del_bom["curve"]), 1)
        self.assertEqual(bc_del_bom["curve"][0]["lead_time_days"], 14)

    def test_empty_database_handling(self):
        result = rebuild_route_indices()
        self.assertEqual(result["rows_written"], 0)

        nat = get_national_composite_index()
        self.assertEqual(nat["values"], [])
        self.assertIsNone(nat["latest_value"])

        summary = get_routes_summary()
        self.assertEqual(summary, [])

        bc = get_booking_curve_analytics("NON_EXISTENT")
        self.assertEqual(bc["total_observations"], 0)
        self.assertEqual(bc["curve"], [])

    def test_legacy_round_trip_and_unknown_excluded_from_public_calculations(self):
        """
        Verifies that ROUND_TRIP_LEGACY and UNKNOWN records are strictly excluded from
        public calculations, but remain in the database for provenance and audit.
        """
        conn = sqlite3.connect(self.db_path)
        rows = [
            # Legitimate ONE_WAY observations
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 7500.0, "2026-09-15", "2026-09-07T10:00:00+00:00", "ONE_WAY", "VALID"),
            ("HYD-DEL", "HYD", "DEL", "Air India", "Playwright Scraper", 8500.0, "2026-09-15", "2026-09-07T10:00:00+00:00", "ONE_WAY", "VALID"),
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 8000.0, "2026-09-15", "2026-09-08T10:00:00+00:00", "ONE_WAY", "VALID"),
            ("HYD-DEL", "HYD", "DEL", "Air India", "Playwright Scraper", 9000.0, "2026-09-15", "2026-09-08T10:00:00+00:00", "ONE_WAY", "VALID"),
            # Legacy Round Trip records (high price, e.g. ₹18,000)
            ("HYD-DEL", "HYD", "DEL", "LegacyAir", "Playwright Scraper", 18000.0, "2026-09-15", "2026-09-08T10:00:00+00:00", "ROUND_TRIP_LEGACY", "INVALID"),
            ("HYD-DEL", "HYD", "DEL", "LegacyAir", "Playwright Scraper", 19000.0, "2026-09-15", "2026-09-08T10:00:00+00:00", "ROUND_TRIP_LEGACY", "INVALID"),
            # Unknown fare type records
            ("HYD-DEL", "HYD", "DEL", "UnknownAir", "Unknown", 12000.0, "2026-09-15", "2026-09-08T10:00:00+00:00", "UNKNOWN", "UNKNOWN"),
        ]
        conn.executemany("""
            INSERT INTO raw_prices (route, origin, destination, airline, source, price_inr, travel_date, search_timestamp, fare_type, domestic_eligibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()

        # Check public snapshot
        snap = get_public_snapshot_dataframe(conn, "HYD-DEL")
        self.assertEqual(len(snap), 4) # Only 4 ONE_WAY records included
        self.assertNotIn("LegacyAir", snap["airline"].values)
        self.assertNotIn("UnknownAir", snap["airline"].values)

        # Rebuild index and verify avg_fare on Sep 8 is (8000+9000)/2 = 8500 (not polluted by 18000/19000)
        rebuild_route_indices()
        conn.row_factory = sqlite3.Row
        idx = conn.execute("SELECT * FROM index_values WHERE route = 'HYD-DEL' AND observation_date = '2026-09-08'").fetchone()
        self.assertAlmostEqual(idx["avg_fare"], 8500.0)

        # Provenance summary still counts legacy & unknown rows for audit
        prov = get_provenance_summary()
        self.assertEqual(prov["total"], 7)
        self.assertEqual(prov["one_way"], 4)
        self.assertEqual(prov["legacy_round_trip"], 2)
        self.assertEqual(prov["unknown"], 1)
        conn.close()

    def test_longitudinal_multiple_observation_dates_for_same_travel_date(self):
        """
        Verifies that observations for the same flight/travel date across multiple observation dates
        are both preserved as valid longitudinal data.
        """
        conn = sqlite3.connect(self.db_path)
        rows = [
            # Travel date Sep 15 observed on Sep 7
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 8000.0, "2026-09-15", "2026-09-07T10:00:00+00:00", "ONE_WAY", "VALID"),
            # Same Travel date Sep 15 observed on Sep 8
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 8500.0, "2026-09-15", "2026-09-08T10:00:00+00:00", "ONE_WAY", "VALID"),
        ]
        conn.executemany("""
            INSERT INTO raw_prices (route, origin, destination, airline, source, price_inr, travel_date, search_timestamp, fare_type, domestic_eligibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()

        snap = get_public_snapshot_dataframe(conn, "HYD-DEL")
        self.assertEqual(len(snap), 2) # Both preserved across observation dates
        rebuild_route_indices()
        conn.row_factory = sqlite3.Row
        indices = conn.execute("SELECT * FROM index_values WHERE route = 'HYD-DEL' ORDER BY observation_date").fetchall()
        self.assertEqual(len(indices), 2)
        self.assertAlmostEqual(indices[0]["avg_fare"], 8000.0)
        self.assertAlmostEqual(indices[1]["avg_fare"], 8500.0)
        conn.close()

if __name__ == "__main__":
    unittest.main()
