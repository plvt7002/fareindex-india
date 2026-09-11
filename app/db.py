from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterable, Optional, Union

import pandas as pd

from .config import (
    DB_PATH,
    TURSO_AUTH_TOKEN,
    TURSO_DATABASE_URL,
    get_turso_https_url,
    is_turso_configured,
)

logger = logging.getLogger("fareindex.db")


def sanitize_message(msg: str) -> str:
    """Helper to redact sensitive token from any output or exception trace."""
    if TURSO_AUTH_TOKEN and TURSO_AUTH_TOKEN in msg:
        return msg.replace(TURSO_AUTH_TOKEN, "[REDACTED_AUTH_TOKEN]")
    return msg


class TursoRow:
    """
    Provides dictionary-like and index-based row access matching sqlite3.Row semantics.
    Supports dict(row), row['col'], row[0], and 'col' in row.keys().
    """

    __slots__ = ("_columns", "_values", "_col_map")

    def __init__(self, columns: tuple[str, ...], values: tuple[Any, ...]):
        self._columns = tuple(columns)
        self._values = tuple(values)
        self._col_map = {c: i for i, c in enumerate(columns)}

    def __getitem__(self, key: Union[int, str]) -> Any:
        if isinstance(key, int):
            return self._values[key]
        idx = self._col_map.get(key)
        if idx is None:
            raise KeyError(f"No such column: {key}")
        return self._values[idx]

    def get(self, key: str, default: Any = None) -> Any:
        idx = self._col_map.get(key)
        if idx is None:
            return default
        return self._values[idx]

    def __iter__(self):
        return iter(self._columns)

    def keys(self) -> tuple[str, ...]:
        return self._columns

    def values(self) -> tuple[Any, ...]:
        return self._values

    def items(self):
        return zip(self._columns, self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return f"<TursoRow {dict(self)}>"


class TursoResultWrapper:
    """Wraps a libsql_client.ResultSet to provide DB-API style fetchall / fetchone."""

    def __init__(self, result_set: Any):
        self._columns = tuple(result_set.columns)
        self._rows = [TursoRow(self._columns, tuple(r)) for r in result_set.rows]
        self._iter = iter(self._rows)

    @property
    def columns(self) -> tuple[str, ...]:
        return self._columns

    @property
    def rows(self) -> list[TursoRow]:
        return self._rows

    def fetchall(self) -> list[TursoRow]:
        return self._rows

    def fetchone(self) -> Optional[TursoRow]:
        try:
            return next(self._iter)
        except StopIteration:
            return None

    def __iter__(self):
        return iter(self._rows)

    def __len__(self) -> int:
        return len(self._rows)


class TursoConnectionWrapper:
    """Wraps a libsql_client.ClientSync to provide a sqlite3-compatible interface."""

    def __init__(self, client: Any):
        self._client = client
        self._is_closed = False

    def execute(self, sql: str, params: Union[tuple, list, None] = None) -> TursoResultWrapper:
        p = list(params) if params is not None else []
        try:
            res = self._client.execute(sql, p)
            return TursoResultWrapper(res)
        except Exception as exc:
            clean_msg = sanitize_message(str(exc))
            raise RuntimeError(f"Turso execute error: {clean_msg}") from None

    def executemany(self, sql: str, seq_of_params: Iterable[Union[tuple, list]]) -> list[TursoResultWrapper]:
        import libsql_client

        stmts = [libsql_client.Statement(sql, list(p)) for p in seq_of_params]
        if not stmts:
            return []
        try:
            res_list = self._client.batch(stmts)
            return [TursoResultWrapper(r) for r in res_list]
        except Exception as exc:
            clean_msg = sanitize_message(str(exc))
            raise RuntimeError(f"Turso batch execute error: {clean_msg}") from None

    def cursor(self) -> TursoCursorWrapper:
        return TursoCursorWrapper(self)

    def commit(self) -> None:
        # Turso statements executed over HTTP pipeline are committed atomically
        pass

    def close(self) -> None:
        if not self._is_closed:
            try:
                self._client.close()
            except Exception:
                pass
            self._is_closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type:
            self.commit()
        self.close()


class TursoCursorWrapper:
    """Cursor wrapper for Turso connection."""

    def __init__(self, conn: TursoConnectionWrapper):
        self._conn = conn
        self._last_result: Optional[TursoResultWrapper] = None

    def execute(self, sql: str, params: Union[tuple, list, None] = None) -> TursoCursorWrapper:
        self._last_result = self._conn.execute(sql, params)
        return self

    def executemany(self, sql: str, seq_of_params: Iterable[Union[tuple, list]]) -> TursoCursorWrapper:
        self._last_result = None
        self._conn.executemany(sql, seq_of_params)
        return self

    def fetchall(self) -> list[TursoRow]:
        if self._last_result is None:
            return []
        return self._last_result.fetchall()

    def fetchone(self) -> Optional[TursoRow]:
        if self._last_result is None:
            return None
        return self._last_result.fetchone()

    def close(self) -> None:
        pass


def connect() -> Any:
    """
    Returns an active database connection:
    - If Turso credentials exist (TURSO_DATABASE_URL + TURSO_AUTH_TOKEN), connects to Turso via HTTPS.
    - Otherwise, falls back to local SQLite at DB_PATH.
    """
    if is_turso_configured():
        import libsql_client

        https_url = get_turso_https_url()
        client = libsql_client.create_client_sync(url=https_url, auth_token=TURSO_AUTH_TOKEN)
        return TursoConnectionWrapper(client)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db():
    """Context manager for database connections, committing on success and closing on exit."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def query_df(sql: str, params: Union[tuple, list, None] = None, conn: Any = None) -> pd.DataFrame:
    """
    Executes a SELECT query and returns a pandas DataFrame with identical columns and data.
    Works transparently on both local SQLite and remote Turso connections.
    """
    close_after = False
    if conn is None:
        conn = connect()
        close_after = True
    try:
        if is_turso_configured() or isinstance(conn, TursoConnectionWrapper):
            res = conn.execute(sql, params)
            if not res.rows:
                return pd.DataFrame([], columns=list(res.columns))
            data = [list(r.values()) for r in res.rows]
            return pd.DataFrame(data, columns=list(res.columns))
        else:
            p = list(params) if params is not None else []
            return pd.read_sql_query(sql, conn, params=p)
    finally:
        if close_after:
            conn.close()


def migrate_schema(conn: Any):
    """
    Safely adds fare_type and domestic_eligibility columns if missing and migrates legacy rows.
    Preserves all row counts, prices, timestamps, and route details on SQLite and Turso.
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
    """Initializes tables, indexes, and applies schema migrations on active database."""
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
