"""
DatabaseConnector – a thin wrapper around SQLAlchemy that supports
SQLite, PostgreSQL, MySQL/MariaDB, Microsoft SQL Server, Oracle,
IBM DB2, Snowflake, CockroachDB, Altibase, Firebird, SAP HANA,
ClickHouse, and DuckDB.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# Map short driver names to SQLAlchemy dialect strings.
# The caller only needs to pass the 'db_type' key; the full dialect is
# resolved here so the rest of the codebase stays clean.
_DIALECT_MAP: Dict[str, str] = {
    # ── Relational (open-source / free) ───────────────────────────────
    "sqlite": "sqlite",
    "postgresql": "postgresql+psycopg2",
    "postgres": "postgresql+psycopg2",       # alias
    "mysql": "mysql+pymysql",
    "mariadb": "mysql+pymysql",              # alias
    "firebird": "firebird+fdb",
    "cockroachdb": "cockroachdb+psycopg2",
    "duckdb": "duckdb",                      # file-based like SQLite
    # ── Relational (commercial / enterprise) ──────────────────────────
    "mssql": "mssql+pyodbc",
    "sqlserver": "mssql+pyodbc",             # alias
    "oracle": "oracle+cx_oracle",
    "db2": "ibm_db_sa+ibm_db",
    "altibase": "altibase+pyodbc",
    "hana": "hana+hdbcli",
    "saphana": "hana+hdbcli",               # alias
    # ── Cloud / analytics ─────────────────────────────────────────────
    "snowflake": "snowflake",
    "clickhouse": "clickhouse+native",
}


class DatabaseConnector:
    """Connect to a database and run SQL queries.

    Parameters
    ----------
    db_type:
        One of ``sqlite``, ``postgresql`` / ``postgres``,
        ``mysql`` / ``mariadb``, ``mssql`` / ``sqlserver``,
        ``oracle``, ``db2``, ``snowflake``, ``cockroachdb``,
        ``altibase``, ``firebird``, ``hana`` / ``saphana``,
        ``clickhouse``, or ``duckdb``.
    database:
        Database name (or file path for SQLite / DuckDB).
    host:
        Hostname or IP address (not required for SQLite / DuckDB).
        For Snowflake, pass the *account identifier* here.
    port:
        TCP port (uses the driver default when omitted).
    username:
        Login user (not required for SQLite / DuckDB).
    password:
        Login password (not required for SQLite / DuckDB).
    **engine_kwargs:
        Extra keyword arguments forwarded to :func:`sqlalchemy.create_engine`.

    Examples
    --------
    SQLite (no credentials needed)::

        conn = DatabaseConnector(db_type="sqlite", database="mydb.sqlite")
        conn.connect()
        rows, cols = conn.execute_query("SELECT * FROM users")
        conn.disconnect()

    PostgreSQL::

        conn = DatabaseConnector(
            db_type="postgresql",
            host="localhost",
            database="mydb",
            username="alice",
            password="secret",
        )
    """

    def __init__(
        self,
        db_type: str,
        database: str,
        host: str = "localhost",
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        **engine_kwargs: Any,
    ) -> None:
        self.db_type = db_type.lower()
        self.database = database
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._engine_kwargs = engine_kwargs

        self._engine: Optional[Engine] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Create the SQLAlchemy engine and verify the connection."""
        url = self._build_url()
        self._engine = create_engine(url, **self._engine_kwargs)
        # Touch the database to surface any connection problems early.
        with self._engine.connect():
            pass

    def disconnect(self) -> None:
        """Dispose of the connection pool."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None

    def execute_query(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Tuple[Any, ...]], List[str]]:
        """Run *query* and return ``(rows, column_names)``.

        Parameters
        ----------
        query:
            A SQL statement.  Use ``:name`` placeholders for bound
            parameters (SQLAlchemy *named* style).
        params:
            Mapping of parameter names to values.

        Returns
        -------
        rows:
            List of row tuples.
        columns:
            List of column name strings (empty for non-SELECT statements).
        """
        if self._engine is None:
            raise RuntimeError("Not connected. Call connect() first.")

        with self._engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            if result.returns_rows:
                columns = list(result.keys())
                rows = result.fetchall()
                return [tuple(row) for row in rows], columns
            conn.commit()
            return [], []

    def list_tables(self) -> List[str]:
        """Return a list of table names in the current database/schema."""
        if self._engine is None:
            raise RuntimeError("Not connected. Call connect() first.")

        from sqlalchemy import inspect as sa_inspect

        inspector = sa_inspect(self._engine)
        return inspector.get_table_names()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_url(self) -> str:
        """Assemble a SQLAlchemy connection URL from the stored parameters."""
        db_key = self.db_type
        if db_key not in _DIALECT_MAP:
            supported = ", ".join(sorted(_DIALECT_MAP.keys()))
            raise ValueError(
                f"Unsupported db_type '{self.db_type}'. "
                f"Supported types: {supported}"
            )

        dialect = _DIALECT_MAP[db_key]

        if db_key in ("sqlite", "duckdb"):
            # sqlite:///path  or  duckdb:///path  (file-based, no credentials)
            return f"{db_key}:///{self.database}"

        # All other engines need host / credentials.
        user = quote_plus(self.username or "")
        pwd = f":{quote_plus(self.password)}" if self.password else ""
        host = self.host or "localhost"
        port_str = f":{self.port}" if self.port else ""

        if db_key in ("mssql", "sqlserver"):
            # pyodbc requires a driver name in the query string.
            return (
                f"{dialect}://{user}{pwd}@{host}{port_str}/{self.database}"
                "?driver=ODBC+Driver+17+for+SQL+Server"
            )

        return f"{dialect}://{user}{pwd}@{host}{port_str}/{self.database}"

    def __repr__(self) -> str:
        connected = self._engine is not None
        return (
            f"DatabaseConnector(db_type={self.db_type!r}, "
            f"database={self.database!r}, connected={connected})"
        )
