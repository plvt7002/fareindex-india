import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/fareindex.db")
DB_PATH = (BASE_DIR / DATABASE_PATH).resolve()

FARE_PROVIDER = os.getenv("FARE_PROVIDER", "demo").strip().lower()
SCRAPE_INTERVAL_HOURS = int(os.getenv("SCRAPE_INTERVAL_HOURS", "24"))

TRACKED_ROUTES = [
    x.strip().upper()
    for x in os.getenv("TRACKED_ROUTES", "HYD-DEL,HYD-GOI").split(",")
    if x.strip()
]

BOOKING_WINDOWS_DAYS = [
    int(x.strip())
    for x in os.getenv("BOOKING_WINDOWS_DAYS", "7,14,21,30,60").split(",")
    if x.strip()
]

AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID", "")
AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET", "")

PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").strip().lower() in ("true", "1", "yes")
PLAYWRIGHT_TIMEOUT_MS = int(os.getenv("PLAYWRIGHT_TIMEOUT_MS", "25000"))

# Route-importance weights used for National Composite Index.
# In production, these will be based on DGCA domestic passenger traffic share.
# For the Hackathon MVP, explicit provisional demonstration weights are provided.
DEFAULT_ROUTE_WEIGHTS: dict[str, float] = {
    "HYD-DEL": 1.0,
    "DEL-BOM": 1.5,
    "BOM-BLR": 1.2,
    "DEL-BLR": 1.3,
    "HYD-GOI": 0.6,
    "MAA-DEL": 0.9,
    "CCU-DEL": 0.8,
}

def parse_route_weights() -> dict[str, float]:
    raw = os.getenv("ROUTE_WEIGHTS", "").strip()
    if not raw:
        return dict(DEFAULT_ROUTE_WEIGHTS)
    weights = dict(DEFAULT_ROUTE_WEIGHTS)
    for pair in raw.split(","):
        if ":" in pair:
            route, weight_str = pair.split(":", 1)
            try:
                weights[route.strip().upper()] = float(weight_str.strip())
            except ValueError:
                pass
    return weights

ROUTE_WEIGHTS = parse_route_weights()

