"""
==============================================================================
MODULE: database.py
DESCRIPTION: PostgreSQL Database Persistence Layer using psycopg2-binary.
==============================================================================

EDUCATIONAL ARCHITECTURE NOTES:
1. Raw SQL vs. ORM:
   Per the architectural blueprint, we utilize raw SQL executed via psycopg2.
   This guarantees full transparency into query execution plans, avoids ORM
   overhead, and illustrates clean, production-grade parameterized queries
   that guard against SQL Injection (CWE-89).

2. Connection Management & Resilience:
   - Uses context managers to ensure transactions are safely committed or
     rolled back upon unhandled exceptions.
   - Idempotent Schema Creation: Employs 'CREATE TABLE IF NOT EXISTS' so the
     schema auto-initializes on startup without manual migration scripts.
   - Dual-Engine Developer Fallback: If PostgreSQL credentials are not yet
     configured by the engineer, seamlessly falls back to a local SQLite
     engine with identical queries, enabling immediate end-to-end execution.
"""

from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Any

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from config import db_config
from models import InventoryItem


class DatabaseManager:
    """
    Manages database connections, schema generation, and CRUD operations
    for the inventory persistence layer.
    """

    def __init__(self) -> None:
        self.config = db_config
        self.is_sqlite_fallback: bool = False
        self.sqlite_db_path: Path = Path(__file__).resolve().parent / "expiry_tracker.db"
        self._init_connection()

    def _init_connection(self) -> None:
        """
        Attempts to establish connection with PostgreSQL. If connection fails
        and fallback_to_sqlite is enabled, switches to local SQLite engine.
        """
        try:
            conn = self._get_postgres_connection()
            conn.close()
            self.is_sqlite_fallback = False
            self.create_tables()
        except Exception as pg_err:
            if self.config.fallback_to_sqlite:
                self.is_sqlite_fallback = True
                self.create_tables()
            else:
                raise ConnectionError(
                    f"CRITICAL: Failed to connect to PostgreSQL at {self.config.host}:{self.config.port} "
                    f"for user '{self.config.user}'. Error: {pg_err}"
                ) from pg_err

    def _get_postgres_connection(self) -> psycopg2.extensions.connection:
        """
        Opens a new direct connection to PostgreSQL using psycopg2.
        """
        if self.config.database_url:
            return psycopg2.connect(self.config.database_url)
        return psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            dbname=self.config.name,
            user=self.config.user,
            password=self.config.password,
            connect_timeout=3
        )

    def _get_sqlite_connection(self) -> sqlite3.Connection:
        """
        Opens a connection to the local SQLite fallback database.
        """
        conn = sqlite3.connect(str(self.sqlite_db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def get_cursor(self) -> Generator[Any, None, None]:
        """
        Context manager providing a transactional database cursor.
        Automatically handles COMMIT on success and ROLLBACK on exception.
        """
        if not self.is_sqlite_fallback:
            conn = self._get_postgres_connection()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        else:
            conn = self._get_sqlite_connection()
            try:
                cur = conn.cursor()
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def create_tables(self) -> None:
        """
        Generates the inventory table and indexes if they do not exist.
        Follows idempotent DDL design.
        """
        if not self.is_sqlite_fallback:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                sku VARCHAR(64) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                category VARCHAR(100) DEFAULT 'General',
                expiry_date DATE NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_inventory_expiry ON inventory (expiry_date);
            CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory (sku);
            """
            with self.get_cursor() as cur:
                cur.execute(create_table_sql)
        else:
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                expiry_date TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_inventory_expiry ON inventory (expiry_date);
            CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory (sku);
            """
            conn = self._get_sqlite_connection()
            try:
                conn.executescript(create_table_sql)
            finally:
                conn.close()

    def insert_or_upsert_item(self, item: InventoryItem) -> InventoryItem:
        """
        Inserts a new item or updates an existing item's quantity and expiry date
        using raw SQL with parameterized values.
        """
        expiry_str = item.expiry_date.isoformat()

        if not self.is_sqlite_fallback:
            # PostgreSQL UPSERT with ON CONFLICT DO UPDATE
            sql_query = """
            INSERT INTO inventory (sku, name, category, expiry_date, quantity, updated_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (sku) DO UPDATE SET
                quantity = inventory.quantity + EXCLUDED.quantity,
                expiry_date = EXCLUDED.expiry_date,
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, sku, name, category, expiry_date, quantity, created_at, updated_at;
            """
            with self.get_cursor() as cur:
                cur.execute(sql_query, (item.sku, item.name, item.category, item.expiry_date, item.quantity))
                row = cur.fetchone()
                return InventoryItem(
                    id=row["id"],
                    sku=row["sku"],
                    name=row["name"],
                    category=row["category"],
                    expiry_date=row["expiry_date"],
                    quantity=row["quantity"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
        else:
            # SQLite UPSERT syntax
            sql_query = """
            INSERT INTO inventory (sku, name, category, expiry_date, quantity, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(sku) DO UPDATE SET
                quantity = inventory.quantity + excluded.quantity,
                expiry_date = excluded.expiry_date,
                name = excluded.name,
                category = excluded.category,
                updated_at = datetime('now');
            """
            with self.get_cursor() as cur:
                cur.execute(sql_query, (item.sku, item.name, item.category, expiry_str, item.quantity))
            
            fetched = self.get_item_by_sku(item.sku)
            if fetched is None:
                raise RuntimeError("Failed to retrieve upserted item from database.")
            return fetched

    def get_all_items(self) -> List[InventoryItem]:
        """
        Retrieves all inventory items, ordered by expiry date ascending
        (First-Expiring First-Out).
        """
        sql_query = """
        SELECT id, sku, name, category, expiry_date, quantity, created_at, updated_at
        FROM inventory
        ORDER BY expiry_date ASC, id ASC;
        """
        items: List[InventoryItem] = []
        with self.get_cursor() as cur:
            cur.execute(sql_query)
            rows = cur.fetchall()
            for r in rows:
                raw_exp = r["expiry_date"]
                if isinstance(raw_exp, str):
                    exp_date = date.fromisoformat(raw_exp)
                elif isinstance(raw_exp, datetime):
                    exp_date = raw_exp.date()
                else:
                    exp_date = raw_exp

                items.append(
                    InventoryItem(
                        id=r["id"],
                        sku=r["sku"],
                        name=r["name"],
                        category=r["category"],
                        expiry_date=exp_date,
                        quantity=r["quantity"],
                        created_at=r["created_at"] if isinstance(r["created_at"], datetime) else None,
                        updated_at=r["updated_at"] if isinstance(r["updated_at"], datetime) else None
                    )
                )
        return items

    def get_item_by_sku(self, sku: str) -> Optional[InventoryItem]:
        """
        Fetches a single inventory item by SKU code using case-insensitive match.
        """
        clean_sku = sku.strip().upper()
        if not self.is_sqlite_fallback:
            sql_query = """
            SELECT id, sku, name, category, expiry_date, quantity, created_at, updated_at
            FROM inventory
            WHERE UPPER(sku) = UPPER(%s);
            """
            params = (clean_sku,)
        else:
            sql_query = """
            SELECT id, sku, name, category, expiry_date, quantity, created_at, updated_at
            FROM inventory
            WHERE UPPER(sku) = UPPER(?);
            """
            params = (clean_sku,)

        with self.get_cursor() as cur:
            cur.execute(sql_query, params)
            row = cur.fetchone()
            if not row:
                return None

            raw_exp = row["expiry_date"]
            if isinstance(raw_exp, str):
                exp_date = date.fromisoformat(raw_exp)
            elif isinstance(raw_exp, datetime):
                exp_date = raw_exp.date()
            else:
                exp_date = raw_exp

            return InventoryItem(
                id=row["id"],
                sku=row["sku"],
                name=row["name"],
                category=row["category"],
                expiry_date=exp_date,
                quantity=row["quantity"],
                created_at=row["created_at"] if isinstance(row["created_at"], datetime) else None,
                updated_at=row["updated_at"] if isinstance(row["updated_at"], datetime) else None
            )

    def update_item_quantity(self, sku: str, new_quantity: int) -> bool:
        """
        Updates the physical on-hand quantity for a specific SKU.
        If new_quantity is 0, the record remains in the database with 0 quantity
        until explicitly removed or deleted.
        """
        if new_quantity < 0:
            raise ValueError("Inventory quantity cannot be negative.")

        clean_sku = sku.strip().upper()
        if not self.is_sqlite_fallback:
            sql_query = """
            UPDATE inventory
            SET quantity = %s, updated_at = CURRENT_TIMESTAMP
            WHERE UPPER(sku) = UPPER(%s);
            """
            params = (new_quantity, clean_sku)
        else:
            sql_query = """
            UPDATE inventory
            SET quantity = ?, updated_at = datetime('now')
            WHERE UPPER(sku) = UPPER(?);
            """
            params = (new_quantity, clean_sku)

        with self.get_cursor() as cur:
            cur.execute(sql_query, params)
            # In sqlite3 / psycopg2 rowcount indicates modified rows
            return cur.rowcount > 0

    def delete_item(self, sku: str) -> bool:
        """
        Deletes a specific inventory item by SKU code.
        """
        clean_sku = sku.strip().upper()
        if not self.is_sqlite_fallback:
            sql_query = "DELETE FROM inventory WHERE UPPER(sku) = UPPER(%s);"
            params = (clean_sku,)
        else:
            sql_query = "DELETE FROM inventory WHERE UPPER(sku) = UPPER(?);"
            params = (clean_sku,)

        with self.get_cursor() as cur:
            cur.execute(sql_query, params)
            return cur.rowcount > 0

    def bulk_dispose_expired_items(self, cutoff_date: date) -> int:
        """
        Disposes/removes all inventory records with expiry_date <= cutoff_date.
        Returns the number of deleted records.
        """
        cutoff_str = cutoff_date.isoformat()
        if not self.is_sqlite_fallback:
            sql_query = "DELETE FROM inventory WHERE expiry_date <= %s;"
            params = (cutoff_date,)
        else:
            sql_query = "DELETE FROM inventory WHERE expiry_date <= ?;"
            params = (cutoff_str,)

        with self.get_cursor() as cur:
            cur.execute(sql_query, params)
            return cur.rowcount

    def clear_all(self) -> None:
        """
        Utility function for unit testing to truncate the inventory table.
        """
        with self.get_cursor() as cur:
            if not self.is_sqlite_fallback:
                cur.execute("TRUNCATE TABLE inventory RESTART IDENTITY;")
            else:
                cur.execute("DELETE FROM inventory;")

    def get_status_info(self) -> dict[str, Any]:
        """
        Returns diagnostic information regarding active database engine and host.
        """
        if not self.is_sqlite_fallback:
            return {
                "engine": "PostgreSQL (psycopg2-binary)",
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.name,
                "user": self.config.user,
                "is_fallback": False
            }
        return {
            "engine": "SQLite3 (Local Development Fallback)",
            "file": str(self.sqlite_db_path),
            "is_fallback": True
        }


# Global singleton database manager instance
db_manager = DatabaseManager()
