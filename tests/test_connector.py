"""
Tests for DatabaseConnector using an in-memory SQLite database.
No external services required.
"""

import pytest
from db_connector import DatabaseConnector


@pytest.fixture()
def sqlite_conn():
    """Return a connected in-memory SQLite connector; disconnect after test."""
    conn = DatabaseConnector(db_type="sqlite", database=":memory:")
    conn.connect()
    yield conn
    conn.disconnect()


# ---------------------------------------------------------------------------
# Connection tests
# ---------------------------------------------------------------------------

def test_connect_sqlite():
    conn = DatabaseConnector(db_type="sqlite", database=":memory:")
    conn.connect()
    assert conn._engine is not None
    conn.disconnect()
    assert conn._engine is None


def test_repr_connected(sqlite_conn):
    assert "connected=True" in repr(sqlite_conn)


def test_repr_disconnected():
    conn = DatabaseConnector(db_type="sqlite", database=":memory:")
    assert "connected=False" in repr(conn)


# ---------------------------------------------------------------------------
# URL-building tests
# ---------------------------------------------------------------------------

def test_url_sqlite():
    conn = DatabaseConnector(db_type="sqlite", database="mydb.db")
    assert conn._build_url() == "sqlite:///mydb.db"


def test_url_postgresql():
    conn = DatabaseConnector(
        db_type="postgresql",
        host="pg-host",
        port=5432,
        database="testdb",
        username="alice",
        password="secret",
    )
    assert conn._build_url() == (
        "postgresql+psycopg2://alice:secret@pg-host:5432/testdb"
    )


def test_url_mysql():
    conn = DatabaseConnector(
        db_type="mysql",
        host="db-host",
        database="shop",
        username="root",
        password="pass",
    )
    url = conn._build_url()
    assert url.startswith("mysql+pymysql://root:pass@db-host/shop")


def test_url_mssql_contains_driver():
    conn = DatabaseConnector(
        db_type="mssql",
        host="sql-host",
        database="warehouse",
        username="sa",
        password="P@ssw0rd",
    )
    url = conn._build_url()
    assert "mssql+pyodbc" in url
    assert "ODBC+Driver" in url


def test_url_special_chars_encoded():
    """Passwords with special chars must be percent-encoded in the URL."""
    conn = DatabaseConnector(
        db_type="postgresql",
        host="pg-host",
        database="mydb",
        username="alice@corp",
        password="p@ss:w/ord",
    )
    url = conn._build_url()
    assert "@corp" not in url or url.count("@") == 1  # only one @ (host separator)
    assert "p@ss" not in url  # raw @ must be encoded
    assert "%40" in url  # url-encoded @



    conn = DatabaseConnector(db_type="oracle", database="orcl")
    with pytest.raises(ValueError, match="Unsupported db_type"):
        conn._build_url()


# ---------------------------------------------------------------------------
# Query tests (SQLite in-memory)
# ---------------------------------------------------------------------------

def test_execute_creates_table(sqlite_conn):
    rows, cols = sqlite_conn.execute_query(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"
    )
    assert rows == []
    assert cols == []


def test_execute_insert_and_select(sqlite_conn):
    sqlite_conn.execute_query(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, label TEXT)"
    )
    sqlite_conn.execute_query("INSERT INTO items (label) VALUES ('alpha')")
    sqlite_conn.execute_query("INSERT INTO items (label) VALUES ('beta')")

    rows, cols = sqlite_conn.execute_query("SELECT * FROM items ORDER BY id")

    assert cols == ["id", "label"]
    assert len(rows) == 2
    assert rows[0][1] == "alpha"
    assert rows[1][1] == "beta"


def test_execute_with_params(sqlite_conn):
    sqlite_conn.execute_query(
        "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)"
    )
    sqlite_conn.execute_query(
        "INSERT INTO products (name, price) VALUES (:name, :price)",
        {"name": "Widget", "price": 9.99},
    )
    rows, cols = sqlite_conn.execute_query(
        "SELECT name, price FROM products WHERE name = :name",
        {"name": "Widget"},
    )
    assert len(rows) == 1
    assert rows[0] == ("Widget", 9.99)


def test_execute_raises_when_not_connected():
    conn = DatabaseConnector(db_type="sqlite", database=":memory:")
    with pytest.raises(RuntimeError, match="Not connected"):
        conn.execute_query("SELECT 1")


def test_list_tables(sqlite_conn):
    sqlite_conn.execute_query("CREATE TABLE t1 (x INTEGER)")
    sqlite_conn.execute_query("CREATE TABLE t2 (y TEXT)")
    tables = sqlite_conn.list_tables()
    assert "t1" in tables
    assert "t2" in tables


def test_list_tables_raises_when_not_connected():
    conn = DatabaseConnector(db_type="sqlite", database=":memory:")
    with pytest.raises(RuntimeError, match="Not connected"):
        conn.list_tables()
