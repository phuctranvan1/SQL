# SQL – Multi-Database Connector

A Python application that connects to many kinds of databases and lets you run SQL queries through an interactive CLI or a reusable library.

## Supported databases

| Database | `db_type` value |
|---|---|
| SQLite | `sqlite` |
| PostgreSQL | `postgresql` or `postgres` |
| MySQL / MariaDB | `mysql` or `mariadb` |
| Microsoft SQL Server | `mssql` or `sqlserver` |
| Oracle | `oracle` |
| IBM DB2 | `db2` |
| Snowflake | `snowflake` |
| CockroachDB | `cockroachdb` |
| Altibase | `altibase` |
| Firebird | `firebird` |
| SAP HANA | `hana` or `saphana` |
| ClickHouse | `clickhouse` |
| DuckDB | `duckdb` |

## Installation

```bash
pip install -r requirements.txt
```

> **Note:** Additional drivers are needed depending on the database:
> - **PostgreSQL** – `psycopg2` + `libpq` on your OS
> - **MySQL / MariaDB** – `pymysql`
> - **MSSQL** – `pyodbc` + *ODBC Driver 17 for SQL Server*
> - **Oracle** – `cx_Oracle` + Oracle Instant Client
> - **IBM DB2** – `ibm_db` + `ibm_db_sa`
> - **Snowflake** – `snowflake-sqlalchemy`
> - **CockroachDB** – `sqlalchemy-cockroachdb` + `psycopg2`
> - **Altibase** – `sqlalchemy-altibase` + `pyodbc` + Altibase ODBC driver
> - **Firebird** – `fdb`
> - **SAP HANA** – `hdbcli` + `sqlalchemy-hana`
> - **ClickHouse** – `clickhouse-sqlalchemy`
> - **DuckDB** – `duckdb-engine`

## Quick start

### Interactive CLI

```bash
python -m db_connector.cli
```

The CLI will prompt you for connection details and then drop you into a SQL REPL:

```
=== Database Connection Setup ===
Supported types: mariadb, mssql, mysql, postgresql, sqlite
Database type [sqlite]: sqlite
Database file (or :memory:) [:memory:]:

Connecting to DatabaseConnector(db_type='sqlite', database=':memory:', connected=False) …
  ✓ Connected!

Enter SQL statements (type 'exit' or 'quit' to disconnect).
Type '\tables' to list all tables.

sql> CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
  ✓ Query executed successfully.

sql> INSERT INTO users VALUES (1, 'Alice');
  ✓ Query executed successfully.

sql> SELECT * FROM users;
+------+--------+
|   id | name   |
|------+--------|
|    1 | Alice  |
+------+--------+
  (1 row returned)

sql> \tables
+--------+
| Table  |
+--------+
| users  |
+--------+

sql> exit
Disconnected. Bye!
```

### Library usage

```python
from db_connector import DatabaseConnector

# SQLite (no credentials needed)
conn = DatabaseConnector(db_type="sqlite", database="mydb.sqlite")
conn.connect()

rows, columns = conn.execute_query("SELECT * FROM users WHERE id = :uid", {"uid": 1})
print(columns)  # ['id', 'name']
print(rows)     # [(1, 'Alice')]

tables = conn.list_tables()
conn.disconnect()

# PostgreSQL
conn = DatabaseConnector(
    db_type="postgresql",
    host="localhost",
    port=5432,
    database="mydb",
    username="alice",
    password="secret",
)
conn.connect()
rows, cols = conn.execute_query("SELECT version()")
conn.disconnect()
```

## Running the tests

```bash
pip install pytest
python -m pytest tests/ -v
```
