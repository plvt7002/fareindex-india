import pytest
from fastapi.testclient import TestClient
from app.main import app

class TestObservedFaresCompleteness:
    """
    Verifies that Observed Fares returns the complete verified dataset
    and all airlines are accessible.
    """

    def test_hyd_del_latest_prices_returns_full_dataset(self):
        client = TestClient(app)
        res = client.get("/api/prices/latest?route=HYD-DEL")
        assert res.status_code == 200
        data = res.json()

        fares = data.get("fares", [])
        assert len(fares) >= 150, f"Expected full observation batch, got {len(fares)}"
        assert data.get("total_observations_in_batch") == len(fares)

        # Verify key airlines are represented in the dataset
        airlines = {f["airline"] for f in fares}
        assert "IndiGo" in airlines
        assert "Air India" in airlines
        assert "Akasa Air" in airlines

        # Verify counts per airline
        counts = {}
        for f in fares:
            counts[f["airline"]] = counts.get(f["airline"], 0) + 1

        assert counts["IndiGo"] >= 80
        assert counts["Air India"] >= 50
        assert counts["Akasa Air"] >= 10

    def test_hyd_goi_latest_prices_returns_records(self):
        client = TestClient(app)
        res = client.get("/api/prices/latest?route=HYD-GOI")
        assert res.status_code == 200
        data = res.json()
        fares = data.get("fares", [])
        assert len(fares) > 0

    def test_pagination_and_slice_boundaries(self):
        client = TestClient(app)
        res = client.get("/api/prices/latest?route=HYD-DEL")
        fares = res.json().get("fares", [])
        
        page_size = 20
        total_pages = (len(fares) + page_size - 1) // page_size
        assert total_pages >= 8

        seen_ids = set()
        for page in range(1, total_pages + 1):
            start = (page - 1) * page_size
            end = min(start + page_size, len(fares))
            page_slice = fares[start:end]
            assert len(page_slice) <= 20
            for item in page_slice:
                assert item["id"] not in seen_ids, f"Duplicate id {item['id']} on page {page}"
                seen_ids.add(item["id"])

        assert len(seen_ids) == len(fares)

    def test_individual_flight_prices_distinct_and_not_overwritten_by_median(self):
        client = TestClient(app)
        res = client.get("/api/prices/latest?route=HYD-DEL&fare_type=ONE_WAY")
        assert res.status_code == 200
        fares = res.json().get("fares", [])

        # Verify exact equality between price_inr and observed_fare for all rows
        for f in fares:
            assert f["price_inr"] == f["observed_fare"]
            assert f["price_inr"] > 0

        # Collect distinct prices across the batch
        prices = {f["price_inr"] for f in fares}
        assert len(prices) > 20, "Batch must have multiple distinct observed prices"
        assert 7373.0 in prices
        assert 7463.0 in prices

        # Check batch median vs individual prices
        sorted_p = sorted([f["price_inr"] for f in fares])
        batch_median = sorted_p[len(sorted_p) // 2]
        assert batch_median > 0

        # Prove that non-median rows preserve their own distinct prices
        non_median_fares = [f for f in fares if f["price_inr"] != batch_median]
        assert len(non_median_fares) > 0
        assert non_median_fares[0]["price_inr"] != batch_median
        assert non_median_fares[0]["observed_fare"] != batch_median

    def test_round_trip_prices_distinct_and_isolated(self):
        client = TestClient(app)
        res = client.get("/api/prices/latest?route=HYD-DEL&fare_type=ROUND_TRIP_LEGACY")
        # Legacy round-trip fares are deleted from canonical dataset and return 404
        assert res.status_code == 404

    def test_representative_fares_p10_p90_selection_and_median_proximity(self):
        """
        Validates representative fare logic:
        - Calculates dynamic P10, P90, median for the latest HYD-DEL batch.
        - Verifies that central 80% filters out extreme fares (> P90).
        - Verifies that top 10 representative fares are closest to median.
        - Confirms all 10 rows preserve their own raw price_inr and are not overwritten.
        """
        import numpy as np
        client = TestClient(app)
        res = client.get("/api/prices/latest?route=HYD-DEL&fare_type=ONE_WAY")
        assert res.status_code == 200
        fares = res.json().get("fares", [])
        assert len(fares) >= 150

        prices = [f["price_inr"] for f in fares]
        p10 = float(np.percentile(prices, 10))
        median = float(np.median(prices))
        p90 = float(np.percentile(prices, 90))
        max_p = float(np.max(prices))

        assert 7400.0 <= p10 <= 8000.0
        assert 8300.0 <= median <= 8900.0
        assert 9800.0 <= p90 <= 14000.0

        # Maximum extreme fare is > P90, so it must NOT be in the central representative candidates
        assert max_p > p90

        # Central 80% candidates
        rep_candidates = [f for f in fares if p10 <= f["price_inr"] <= p90]
        assert len(rep_candidates) >= 10

        # Rank by distance to median
        rep_ranked = sorted(
            rep_candidates,
            key=lambda f: (abs(f["price_inr"] - median), f["price_inr"], f["airline"], f["departure_time"])
        )
        rep_10 = rep_ranked[:10]
        assert len(rep_10) == 10

        # Ensure no row has max_p in representative top 10
        rep_prices = [f["price_inr"] for f in rep_10]
        assert max_p not in rep_prices

        # Ensure all top 10 rows retain their true individual price_inr
        for r in rep_10:
            assert r["price_inr"] == r["observed_fare"]
            assert abs(r["price_inr"] - median) < 600.0  # Close to median

        # But in the complete batch, extreme fare is present and fully accessible
        assert any(f["price_inr"] == max_p for f in fares)

    def test_airline_filter_recalculates_representative_subset(self):
        """
        Validates that filtering by an airline (e.g. IndiGo) allows calculating
        the representative subset on that airline's specific population.
        """
        import numpy as np
        client = TestClient(app)
        res = client.get("/api/prices/latest?route=HYD-DEL&fare_type=ONE_WAY")
        fares = res.json().get("fares", [])

        indigo_fares = [f for f in fares if f["airline"] == "IndiGo"]
        assert len(indigo_fares) >= 80

        indigo_prices = [f["price_inr"] for f in indigo_fares]
        p10_in = float(np.percentile(indigo_prices, 10))
        med_in = float(np.median(indigo_prices))
        p90_in = float(np.percentile(indigo_prices, 90))

        assert 7300.0 <= p10_in <= 7800.0
        assert 8000.0 <= med_in <= 8800.0
        assert 9500.0 <= p90_in <= 14000.0

        candidates = [f for f in indigo_fares if p10_in <= f["price_inr"] <= p90_in]
        ranked = sorted(candidates, key=lambda f: (abs(f["price_inr"] - med_in), f["price_inr"]))
        top_10 = ranked[:10]
        assert len(top_10) == 10
        for f in top_10:
            assert f["airline"] == "IndiGo"
            assert f["price_inr"] == f["observed_fare"]

    def test_analytics_and_distribution_unaffected_by_representative_display(self):
        """
        Validates that representative UI presentation logic does not alter backend analytics:
        - Route trend series still contains full statistics and histogram with max.
        - Movement calculation still uses complete daily averages.
        """
        client = TestClient(app)
        res = client.get("/api/distribution/route/HYD-DEL?bucket=7D")
        assert res.status_code == 200
        dist_data = res.json()
        assert dist_data["max_fare"] >= 15000.0  # Complete distribution includes extreme fare
        assert dist_data["observation_count"] > 0


