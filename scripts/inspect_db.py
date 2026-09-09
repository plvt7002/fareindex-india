import sys
from pathlib import Path

# Add project root to sys.path so script can be run directly: python3 scripts/inspect_db.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import db, init_db

init_db()

with db() as conn:
    print("\nRoutes:")
    for row in conn.execute("""
        SELECT route, COUNT(*) AS rows,
               MIN(substr(search_timestamp,1,10)) AS first_day,
               MAX(substr(search_timestamp,1,10)) AS last_day
        FROM raw_prices
        GROUP BY route
        ORDER BY route
    """):
        print(dict(row))

    print("\nIndex values:")
    for row in conn.execute("""
        SELECT route, observation_date, avg_fare, baseline_fare, index_value
        FROM index_values
        ORDER BY route, observation_date
    """):
        print(dict(row))
