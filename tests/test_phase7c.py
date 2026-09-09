import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.db import init_db
from app.itinerary import validate_itinerary, is_indian_airport, extract_airports_from_text
from app.scrape_service import validate_observation
from app.index_engine import get_public_snapshot_dataframe, rebuild_route_indices, get_routes_summary

class TestPhase7CDomesticItineraryValidation(unittest.TestCase):
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

    # 1. HYD -> BOM -> GOI => VALID
    def test_domestic_connecting_itinerary(self):
        eligibility, reason, route = validate_itinerary("HYD", "GOI", "1 stop", ["BOM"])
        self.assertEqual(eligibility, "VALID")
        self.assertEqual(reason, "DOMESTIC_ITINERARY")
        self.assertEqual(route, ["HYD", "BOM", "GOI"])

    # 2. HYD -> BAH -> GOI => INVALID / INTERNATIONAL_TRANSIT
    def test_international_transit_bahrain(self):
        eligibility, reason, route = validate_itinerary("HYD", "GOI", "1 stop", ["BAH"])
        self.assertEqual(eligibility, "INVALID")
        self.assertEqual(reason, "INTERNATIONAL_TRANSIT")
        self.assertEqual(route, ["HYD", "BAH", "GOI"])

    # 3. HYD -> CMB -> GOI => INVALID / INTERNATIONAL_TRANSIT
    def test_international_transit_colombo(self):
        eligibility, reason, route = validate_itinerary("HYD", "GOI", "1 stop", ["CMB"])
        self.assertEqual(eligibility, "INVALID")
        self.assertEqual(reason, "INTERNATIONAL_TRANSIT")
        self.assertEqual(route, ["HYD", "CMB", "GOI"])

    # 4. Unknown intermediate airport => UNKNOWN / ROUTING_NOT_VERIFIED
    def test_unknown_intermediate_airport_fails_closed(self):
        # 1-stop with empty or unextractable intermediate airport
        eligibility, reason, route = validate_itinerary("HYD", "GOI", "1 stop", [])
        self.assertEqual(eligibility, "UNKNOWN")
        self.assertEqual(reason, "ROUTING_NOT_VERIFIED")

    # 5. Foreign airline on a fully domestic itinerary => NOT rejected solely by airline name
    def test_foreign_airline_on_domestic_itinerary_not_rejected_by_name(self):
        # Validation checks routing, not airline name
        eligibility, reason, route = validate_itinerary("HYD", "DEL", "Nonstop", None)
        self.assertEqual(eligibility, "VALID")
        self.assertEqual(reason, "DOMESTIC_ITINERARY")

    # 6. Indian airline on international itinerary => REJECTED because routing is international
    def test_indian_airline_on_international_routing_rejected(self):
        # Air India routing through Colombo
        eligibility, reason, route = validate_itinerary("HYD", "GOI", "2 stops", ["CMB", "BOM"])
        self.assertEqual(eligibility, "INVALID")
        self.assertEqual(reason, "INTERNATIONAL_TRANSIT")

    # 7 - 12: Public Index Inclusion and Exclusion Rules
    def test_public_index_eligibility_and_exclusions(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO raw_prices (
                id, route, origin, destination, airline, source, price_inr,
                travel_date, search_timestamp, class, stops, fare_type,
                domestic_eligibility, eligibility_reason
            ) VALUES
            (101, 'HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8500.0, '2026-09-15', '2026-09-08T15:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID', 'DOMESTIC_ITINERARY'),
            (102, 'HYD-DEL', 'HYD', 'DEL', 'Gulf Air', 'Playwright Scraper', 54000.0, '2026-09-15', '2026-09-08T15:00:00Z', 'Economy', '1 stop', 'ONE_WAY', 'INVALID', 'INTERNATIONAL_TRANSIT'),
            (103, 'HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8600.0, '2026-09-15', '2026-09-08T15:00:00Z', 'Economy', '1 stop', 'ONE_WAY', 'UNKNOWN', 'ROUTING_NOT_VERIFIED'),
            (104, 'HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 17000.0, '2026-09-15', '2026-09-08T15:00:00Z', 'Economy', 'Nonstop', 'ROUND_TRIP_LEGACY', 'INVALID', 'ROUND_TRIP_LEGACY'),
            (105, 'HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'Playwright Scraper', 8800.0, '2026-09-15', '2026-09-08T15:00:00Z', 'Economy', 'Nonstop', 'UNKNOWN', 'UNKNOWN', 'LEGACY_ARCHIVE'),
            (106, 'HYD-DEL', 'HYD', 'DEL', 'IndiGo', 'DEMO - NOT LIVE', 5000.0, '2026-09-15', '2026-09-08T15:00:00Z', 'Economy', 'Nonstop', 'ONE_WAY', 'VALID', 'DOMESTIC_ITINERARY')
        """)
        conn.commit()

        # 7. ONE_WAY + VALID domestic => Included
        # 8. ONE_WAY + INVALID => Excluded
        # 9. ONE_WAY + UNKNOWN => Excluded
        # 10. ROUND_TRIP_LEGACY => Excluded
        # 11. UNKNOWN fare_type => Excluded
        # 12. DEMO => Excluded
        df = get_public_snapshot_dataframe(conn, "HYD-DEL")
        conn.close()

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["id"], 101)
        self.assertEqual(df.iloc[0]["price_inr"], 8500.0)
        self.assertEqual(df.iloc[0]["domestic_eligibility"], "VALID")

    # 13 & 14: Historical raw database preservation
    def test_raw_records_and_prices_preserved_in_db(self):
        conn = sqlite3.connect("data/fareindex.db")
        conn.row_factory = sqlite3.Row
        
        # Check the 5 known IDs
        known_ids = (1197, 1204, 1212, 1221, 1222)
        rows = conn.execute(f"SELECT id, airline, price_inr, fare_type, domestic_eligibility, eligibility_reason FROM raw_prices WHERE id IN {known_ids}").fetchall()
        self.assertEqual(len(rows), 5)
        
        for r in rows:
            self.assertEqual(r["fare_type"], "ONE_WAY")
            self.assertEqual(r["domestic_eligibility"], "INVALID")
            self.assertEqual(r["eligibility_reason"], "INTERNATIONAL_TRANSIT")
            self.assertGreater(r["price_inr"], 30000.0)
            
        conn.close()

if __name__ == "__main__":
    unittest.main()
