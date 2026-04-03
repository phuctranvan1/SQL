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


def test_url_unsupported_db_type():
    """An unknown db_type should raise ValueError that names the bad type."""
    conn = DatabaseConnector(db_type="unknowndb", database="x")
    with pytest.raises(ValueError, match="unknowndb"):
        conn._build_url()


def test_url_oracle():
    conn = DatabaseConnector(
        db_type="oracle",
        host="ora-host",
        port=1521,
        database="orcl",
        username="scott",
        password="tiger",
    )
    url = conn._build_url()
    assert url.startswith("oracle+cx_oracle://scott:tiger@ora-host:1521/orcl")


def test_url_db2():
    conn = DatabaseConnector(
        db_type="db2",
        host="db2-host",
        database="SAMPLE",
        username="db2admin",
        password="secret",
    )
    url = conn._build_url()
    assert url.startswith("ibm_db_sa+ibm_db://db2admin:secret@db2-host/SAMPLE")


def test_url_snowflake():
    conn = DatabaseConnector(
        db_type="snowflake",
        host="myaccount.us-east-1",
        database="MYDB",
        username="sf_user",
        password="sf_pass",
    )
    url = conn._build_url()
    assert url.startswith("snowflake://sf_user:sf_pass@myaccount.us-east-1/MYDB")


def test_url_cockroachdb():
    conn = DatabaseConnector(
        db_type="cockroachdb",
        host="crdb-host",
        port=26257,
        database="defaultdb",
        username="root",
        password="",
    )
    url = conn._build_url()
    # Empty password → no colon separator before @
    assert url.startswith("cockroachdb+psycopg2://root@crdb-host:26257/defaultdb")


def test_url_altibase():
    conn = DatabaseConnector(
        db_type="altibase",
        host="alti-host",
        port=20300,
        database="mydb",
        username="sys",
        password="manager",
    )
    url = conn._build_url()
    assert url.startswith("altibase+pyodbc://sys:manager@alti-host:20300/mydb")


def test_url_firebird():
    conn = DatabaseConnector(
        db_type="firebird",
        host="fb-host",
        database="/var/db/mydb.fdb",
        username="sysdba",
        password="masterkey",
    )
    url = conn._build_url()
    assert url.startswith("firebird+fdb://sysdba:masterkey@fb-host")


def test_url_hana():
    conn = DatabaseConnector(
        db_type="hana",
        host="hana-host",
        port=30015,
        database="HXE",
        username="SYSTEM",
        password="HanaPass1",
    )
    url = conn._build_url()
    assert url.startswith("hana+hdbcli://SYSTEM:HanaPass1@hana-host:30015/HXE")


def test_url_hana_alias():
    conn = DatabaseConnector(
        db_type="saphana",
        host="hana-host",
        database="HXE",
        username="SYSTEM",
        password="HanaPass1",
    )
    url = conn._build_url()
    assert url.startswith("hana+hdbcli://")


def test_url_clickhouse():
    conn = DatabaseConnector(
        db_type="clickhouse",
        host="ch-host",
        port=9000,
        database="default",
        username="default",
        password="",
    )
    url = conn._build_url()
    # Empty password → no colon separator before @
    assert url.startswith("clickhouse+native://default@ch-host:9000/default")


def test_url_duckdb():
    conn = DatabaseConnector(db_type="duckdb", database="analytics.duckdb")
    assert conn._build_url() == "duckdb:///analytics.duckdb"


def test_url_duckdb_in_memory():
    conn = DatabaseConnector(db_type="duckdb", database=":memory:")
    assert conn._build_url() == "duckdb:///:memory:"


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
