"""Database utilities for PostgreSQL/Supabase access."""

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional

import psycopg
from psycopg.rows import dict_row

from cortana_common.config import get_settings

logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    """Get a database connection with automatic cleanup.
    
    Yields:
        psycopg.Connection: Database connection with dict_row factory.
        
    Example:
        >>> with get_db_connection() as conn:
        ...     with conn.cursor() as cur:
        ...         cur.execute("SELECT * FROM videos WHERE id = %s", (video_id,))
        ...         video = cur.fetchone()
    """
    settings = get_settings()
    
    supabase_url = settings.supabase_url.rstrip("/")
    project_ref = supabase_url.split("//")[1].split(".")[0]
    
    if settings.database_url:
        conn_string = str(settings.database_url)
    else:
        conn_string = f"postgresql://postgres.{project_ref}:5432/postgres"
    
    conn = None
    try:
        conn = psycopg.connect(
            conn_string,
            row_factory=dict_row,
            autocommit=False,
        )
        logger.debug("Database connection established")
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    fetch_one: bool = False,
    fetch_all: bool = False,
) -> Optional[Any]:
    """Execute a SQL query with automatic connection management.
    
    Args:
        query: SQL query string with %s placeholders.
        params: Query parameters tuple.
        fetch_one: If True, return single row.
        fetch_all: If True, return all rows.
        
    Returns:
        Query result(s) or None for non-SELECT queries.
        
    Example:
        >>> video = execute_query(
        ...     "SELECT * FROM videos WHERE id = %s",
        ...     (video_id,),
        ...     fetch_one=True
        ... )
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            
            if fetch_one:
                return cur.fetchone()
            elif fetch_all:
                return cur.fetchall()
            else:
                return None


def execute_many(query: str, params_list: list[tuple]) -> None:
    """Execute a query multiple times with different parameters.
    
    Args:
        query: SQL query string with %s placeholders.
        params_list: List of parameter tuples.
        
    Example:
        >>> execute_many(
        ...     "INSERT INTO segments (video_id, text) VALUES (%s, %s)",
        ...     [(video_id, "text1"), (video_id, "text2")]
        ... )
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, params_list)
