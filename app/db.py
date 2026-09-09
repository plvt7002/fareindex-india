import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def migrate_schema(conn: sqlite3.Connection):
    """
    Safely adds fare_type and domestic_eligibility columns if missing and migrates legacy rows.
    Preserves all row counts, prices, timestamps, and route details.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(raw_prices)")
    existing_columns = [info[1] for info in cursor.fetchall()]

    if "fare_type" not in existing_columns:
        cursor.execute("ALTER TABLE raw_prices ADD COLUMN fare_type TEXT NOT NULL DEFAULT 'UNKNOWN'")
        cursor.execute("UPDATE raw_prices SET fare_type = 'ROUND_TRIP_LEGACY' WHERE source = 'Playwright Scraper'")
        cursor.execute("UPDATE raw_prices SET fare_type = 'UNKNOWN' WHERE source != 'Playwright Scraper' OR source IS NULL")

    if "domestic_eligibility" not in existing_columns:
        cursor.execute("ALTER TABLE raw_prices ADD COLUMN domestic_eligibility TEXT NOT NULL DEFAULT 'UNKNOWN'")
        cursor.execute("ALTER TABLE raw_prices ADD COLUMN eligibility_reason TEXT")
        cursor.execute("ALTER TABLE raw_prices ADD COLUMN intermediate_airports TEXT")

        # 1. Mark known international transit observations as INVALID
        cursor.execute("""
            UPDATE raw_prices
            SET domestic_eligibility = 'INVALID',
                eligibility_reason = 'INTERNATIONAL_TRANSIT'
            WHERE id IN (1197, 1204, 1212, 1222, 1221)
               OR (airline LIKE '%Gulf Air%' OR airline LIKE '%SriLankan%')
        """)

        # 2. Mark verified domestic ONE_WAY observations as VALID
        cursor.execute("""
            UPDATE raw_prices
            SET domestic_eligibility = 'VALID',
                eligibility_reason = 'DOMESTIC_ITINERARY'
            WHERE fare_type = 'ONE_WAY'
              AND (domestic_eligibility IS NULL OR domestic_eligibility != 'INVALID')
        """)

        # 3. Mark legacy round trip observations as INVALID
        cursor.execute("""
            UPDATE raw_prices
            SET domestic_eligibility = 'INVALID',
                eligibility_reason = 'ROUND_TRIP_LEGACY'
            WHERE fare_type = 'ROUND_TRIP_LEGACY'
        """)

        # 4. Mark archive / demo observations as UNKNOWN
        cursor.execute("""
            UPDATE raw_prices
            SET domestic_eligibility = 'UNKNOWN',
                eligibility_reason = 'LEGACY_ARCHIVE'
            WHERE fare_type = 'UNKNOWN'
        """)

    cursor.execute("PRAGMA table_info(index_values)")
    existing_idx_cols = [info[1] for info in cursor.fetchall()]
    if "median_fare" not in existing_idx_cols and len(existing_idx_cols) > 0:
        cursor.execute("ALTER TABLE index_values ADD COLUMN median_fare REAL NOT NULL DEFAULT 0.0")

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            airline TEXT,
            source TEXT,
            price_inr REAL NOT NULL,
            travel_date TEXT,
            search_timestamp TEXT NOT NULL,
            class TEXT,
            stops TEXT,
            departure_time TEXT,
            arrival_time TEXT,
            seats_left TEXT,
            fare_type TEXT NOT NULL DEFAULT 'UNKNOWN',
            domestic_eligibility TEXT NOT NULL DEFAULT 'UNKNOWN',
            eligibility_reason TEXT,
            intermediate_airports TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS index_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route TEXT NOT NULL,
            observation_date TEXT NOT NULL,
            avg_fare REAL NOT NULL,
            median_fare REAL NOT NULL DEFAULT 0.0,
            baseline_fare REAL NOT NULL,
            index_value REAL NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(route, observation_date)
        )
        """)

        # Run migration for existing databases
        migrate_schema(conn)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_route ON raw_prices(route)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_search_ts ON raw_prices(search_timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_travel_date ON raw_prices(travel_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_fare_type ON raw_prices(fare_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_domestic_eligibility ON raw_prices(domestic_eligibility)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_index_route_date ON index_values(route, observation_date)")
