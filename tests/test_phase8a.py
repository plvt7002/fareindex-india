import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd

from app.db import init_db
from app.index_engine import (
    assign_lead_time_bucket,
    get_public_snapshot_dataframe,
    get_route_trend_series,
    get_routes_summary,
    get_collection_health_summary,
)

class TestPhase8ALongitudinalMarketDataset(unittest.TestCase):
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

    # 1. Lead-time bucket calculation
    def test_lead_time_bucket_mapping(self):
        df = pd.DataFrame([
            {"observation_date": "2026-09-08", "travel_date": "2026-09-15"}, # 7 days -> 7D
            {"observation_date": "2026-09-08", "travel_date": "2026-09-22"}, # 14 days -> 14D
            {"observation_date": "2026-09-08", "travel_date": "2026-09-29"}, # 21 days -> 21D
            {"observation_date": "2026-09-08", "travel_date": "2026-10-08"}, # 30 days -> 30D
            {"observation_date": "2026-09-08", "travel_date": "2026-11-07"}, # 60 days -> 60D
        ])
        res = assign_lead_time_bucket(df)
        self.assertEqual(res.loc[0, "lead_time_bucket"], "7D")
        self.assertEqual(res.loc[1, "lead_time_bucket"], "14D")
        self.assertEqual(res.loc[2, "lead_time_bucket"], "21D")
        self.assertEqual(res.loc[3, "lead_time_bucket"], "30D")
        self.assertEqual(res.loc[4, "lead_time_bucket"], "60D")

    # 2. Observation date != travel date
    def test_observation_date_distinct_from_travel_date(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8000.0, '2026-09-20', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID')
        """)
        conn.commit()

        df = get_public_snapshot_dataframe(conn, "HYD-DEL")
        conn.close()

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["observation_date"], "2026-09-08")
        self.assertEqual(df.iloc[0]["travel_date"], "2026-09-20")
        self.assertNotEqual(df.iloc[0]["observation_date"], df.iloc[0]["travel_date"])

    # 3 & 4. Daily snapshot selection per (route, observation_date, lead_time_bucket) without double-weighting
    def test_daily_snapshot_deduplication_per_bucket(self):
        conn = sqlite3.connect(self.db_path)
        # 3 runs on same observation date (Sep 8) for 7D bucket
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8000.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8100.0, '2026-09-15', '2026-09-08T12:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8200.0, '2026-09-15', '2026-09-08T14:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID')
        """)
        conn.commit()

        df = get_public_snapshot_dataframe(conn, "HYD-DEL")
        conn.close()

        # Only the latest run (14:00) should be in public snapshot
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["price_inr"], 8200.0)
        self.assertEqual(df.iloc[0]["search_timestamp"], "2026-09-08T14:00:00Z")

    # 5. Different observation dates remain separate longitudinal observations
    def test_different_observation_dates_retained(self):
        conn = sqlite3.connect(self.db_path)
        # Same flight/travel date observed across 3 separate observation dates
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8000.0, '2026-09-20', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8400.0, '2026-09-20', '2026-09-09T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8700.0, '2026-09-20', '2026-09-10T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID')
        """)
        conn.commit()

        df = get_public_snapshot_dataframe(conn, "HYD-DEL")
        conn.close()

        # All 3 distinct observation dates preserved
        self.assertEqual(len(df), 3)
        self.assertEqual(set(df["observation_date"]), {"2026-09-08", "2026-09-09", "2026-09-10"})

    # 6 & 7. Different lead-time buckets remain separate in trend analysis
    def test_lead_time_buckets_remain_separate_in_trend(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 7000.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 5000.0, '2026-11-07', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID')
        """)
        conn.commit()
        conn.close()

        # Query 7D trend
        res_7d = get_route_trend_series("HYD-DEL", lead_time_bucket="7D")
        self.assertEqual(len(res_7d["series"]), 1)
        self.assertEqual(res_7d["series"][0]["avg_fare"], 7000.0)

        # Query 60D trend
        res_60d = get_route_trend_series("HYD-DEL", lead_time_bucket="60D")
        self.assertEqual(len(res_60d["series"]), 1)
        self.assertEqual(res_60d["series"][0]["avg_fare"], 5000.0)

    # 8 & 9. Insufficient history (< 7 dates) produces building baseline state without faking history
    def test_building_baseline_when_insufficient_history(self):
        conn = sqlite3.connect(self.db_path)
        # 3 observation dates (< 7 required)
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 7000.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 7200.0, '2026-09-16', '2026-09-09T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 7100.0, '2026-09-17', '2026-09-10T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID')
        """)
        conn.commit()
        conn.close()

        res = get_route_trend_series("HYD-DEL", "7D")
        self.assertEqual(res["trend_readiness"], "BUILDING")
        self.assertTrue(res["is_provisional"])
        self.assertIn("Building baseline", res["status_message"])
        self.assertEqual(len(res["series"]), 3)

    # 10. Sufficient history (>= 7 consecutive dates) produces READY benchmark
    def test_ready_benchmark_when_sufficient_history(self):
        conn = sqlite3.connect(self.db_path)
        rows = [
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", 7000.0 + i * 50, f"2026-09-{15+i:02d}", f"2026-09-{8+i:02d}T10:00:00Z", "Economy", "Nonstop", "ONE_WAY", "VALID")
            for i in range(7)
        ]
        conn.executemany("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        conn.close()

        res = get_route_trend_series("HYD-DEL", "7D")
        self.assertEqual(res["trend_readiness"], "READY")
        self.assertFalse(res["is_provisional"])
        self.assertEqual(res["observation_dates_count"], 7)
        self.assertEqual(res["consecutive_observation_dates_count"], 7)

    # 11. Current vs previous fare uses comparable lead-time bucket
    def test_current_vs_previous_fare_change_calculation(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8000.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8400.0, '2026-09-16', '2026-09-09T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID')
        """)
        conn.commit()
        conn.close()

        res = get_route_trend_series("HYD-DEL", "7D")
        self.assertEqual(res["current_avg_fare"], 8400.0)
        self.assertEqual(res["previous_avg_fare"], 8000.0)
        self.assertEqual(res["fare_change_inr"], 400.0)
        self.assertEqual(res["fare_change_pct"], 5.0)
        self.assertEqual(res["trend_direction"], "RISING")

    # 12. Collection health status report
    def test_collection_health_summary(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8000.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 6000.0, '2026-11-07', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID')
        """)
        conn.commit()
        conn.close()

        health = get_collection_health_summary()
        self.assertEqual(len(health), 2)
        hyd_del = next(h for h in health if h["route"] == "HYD-DEL")
        self.assertEqual(hyd_del["observation_dates_count"], 1)
        self.assertEqual(hyd_del["lead_time_counts"]["7D"], 1)
        self.assertEqual(hyd_del["lead_time_counts"]["60D"], 1)
        self.assertEqual(hyd_del["trend_readiness"], "BUILDING")

    # 13. Invalid, legacy, and demo exclusion from public snapshot
    def test_invalid_legacy_demo_excluded_from_public_snapshot(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8000.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 16000.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ROUND_TRIP_LEGACY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Demo Scraper', 7500.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID'),
            ('HYD-DEL', 'HYD', 'DEL', 'Gulf Air', 'Playwright Scraper', 57000.0, '2026-09-15', '2026-09-08T10:00:00Z', 'Economy', '1 stop', 'ONE_WAY', 'INTERNATIONAL_TRANSIT')
        """)
        conn.commit()

        df = get_public_snapshot_dataframe(conn, "HYD-DEL", target_bucket="7D")
        conn.close()

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["price_inr"], 8000.0)
        self.assertEqual(df.iloc[0]["fare_type"], "ONE_WAY")
        self.assertEqual(df.iloc[0]["domestic_eligibility"], "VALID")

    # 14. Typical fare (median) vs Average fare (mean) in 7D bucket
    def test_typical_median_and_average_mean_metrics(self):
        conn = sqlite3.connect(self.db_path)
        # 5 fares: 7500, 8000, 8448, 9500, 18000
        # Median = 8448, Mean = 10289.6
        fares = [7500.0, 8000.0, 8448.0, 9500.0, 18000.0]
        rows = [
            ("HYD-DEL", "HYD", "DEL", "IndiGo", "Playwright Scraper", f, "2026-09-15", "2026-09-08T10:00:00Z", "Economy", "Nonstop", "ONE_WAY", "VALID")
            for f in fares
        ]
        conn.executemany("""
            INSERT INTO raw_prices (
                route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type, domestic_eligibility
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
        conn.close()

        res = get_route_trend_series("HYD-DEL", "7D")
        self.assertEqual(res["current_typical_fare"], 8448.0)
        self.assertEqual(res["current_average_fare"], 10289.6)
        self.assertEqual(res["current_avg_fare"], 10289.6)
        self.assertEqual(res["observation_count"], 5)
        self.assertEqual(res["min_fare"], 7500.0)
        self.assertEqual(res["max_fare"], 18000.0)
        self.assertIsNotNone(res["distribution"])
        self.assertGreater(len(res["distribution"]["bins"]), 0)

    # 15. Real dataset verification against database
    def test_live_dataset_hyd_del_and_hyd_goi_7d(self):
        from app.db import DB_PATH
        # Test against the actual production db file if it exists
        real_db = Path("data/fareindex.db")
        if real_db.exists():
            real_conn = sqlite3.connect(real_db)
            df_del_7d = get_public_snapshot_dataframe(real_conn, "HYD-DEL", "7D")
            self.assertGreaterEqual(len(df_del_7d), 54)
            df_del_7d_sep8 = df_del_7d[df_del_7d["observation_date"] == "2026-09-08"]
            self.assertEqual(len(df_del_7d_sep8), 54)
            self.assertEqual(round(float(df_del_7d_sep8["price_inr"].median()), 2), 8448.0)
            self.assertEqual(round(float(df_del_7d_sep8["price_inr"].mean()), 2), 9950.37)
            self.assertEqual(round(float(df_del_7d_sep8["price_inr"].min()), 2), 7463.0)
            self.assertEqual(round(float(df_del_7d_sep8["price_inr"].max()), 2), 18906.0)

            df_goi_7d = get_public_snapshot_dataframe(real_conn, "HYD-GOI", "7D")
            self.assertGreaterEqual(len(df_goi_7d), 10)
            df_goi_7d_sep8 = df_goi_7d[df_goi_7d["observation_date"] == "2026-09-08"]
            self.assertEqual(len(df_goi_7d_sep8), 10)
            self.assertEqual(round(float(df_goi_7d_sep8["price_inr"].median()), 2), 10876.0)
            self.assertEqual(round(float(df_goi_7d_sep8["price_inr"].mean()), 2), 10883.40)
            real_conn.close()

if __name__ == "__main__":
    unittest.main()
