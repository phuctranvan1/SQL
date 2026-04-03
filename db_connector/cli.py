"""
Interactive command-line interface for the multi-database connector.

Usage
-----
    python -m db_connector.cli

Or via the installed entry-point::

    sql-connect
"""

from __future__ import annotations

import sys
from getpass import getpass
from typing import List, Optional, Tuple, Any

from tabulate import tabulate

from .connector import DatabaseConnector, _DIALECT_MAP

# Show only canonical names (skip 'postgres' alias for 'postgresql', etc.)
_SUPPORTED_TYPES = sorted(set(_DIALECT_MAP.keys()) - {"postgres", "sqlserver"})


def _prompt(msg: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{msg}{suffix}: ").strip()
    return value if value else (default or "")


def _connect_interactive() -> DatabaseConnector:
    """Ask the user for connection details and return a connected connector."""
    print("\n=== Database Connection Setup ===")
    print("Supported types:", ", ".join(_SUPPORTED_TYPES))

    db_type = _prompt("Database type", "sqlite")
    while db_type not in _DIALECT_MAP:
        print(f"  ✗ Unknown type '{db_type}'. Choose from: {', '.join(_SUPPORTED_TYPES)}")
        db_type = _prompt("Database type", "sqlite")

    if db_type == "sqlite":
        database = _prompt("Database file (or :memory:)", ":memory:")
        conn = DatabaseConnector(db_type=db_type, database=database)
    else:
        host = _prompt("Host", "localhost")
        port_str = _prompt("Port (leave blank for default)", "")
        port = int(port_str) if port_str else None
        database = _prompt("Database name")
        username = _prompt("Username")
        password = getpass("Password: ")
        conn = DatabaseConnector(
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
        )

    print(f"\nConnecting to {conn!r} …")
    conn.connect()
    print("  ✓ Connected!\n")
    return conn


def _run_repl(conn: DatabaseConnector) -> None:
    """Read-Eval-Print Loop: accept SQL statements until the user quits."""
    print("Enter SQL statements (type 'exit' or 'quit' to disconnect).")
    print("Type '\\tables' to list all tables.\n")

    buffer: List[str] = []

    while True:
        prompt_str = "sql> " if not buffer else "   > "
        try:
            line = input(prompt_str)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        stripped = line.strip()

        if not stripped:
            continue

        if stripped.lower() in ("exit", "quit", "\\q"):
            break

        if stripped.lower() == "\\tables":
            tables = conn.list_tables()
            if tables:
                print(tabulate([[t] for t in tables], headers=["Table"]))
            else:
                print("  (no tables found)")
            print()
            continue

        buffer.append(line)

        # Execute when the statement ends with a semicolon (or is complete).
        full_stmt = " ".join(buffer).strip()
        if full_stmt.endswith(";") or ";" in full_stmt:
            query = full_stmt.rstrip(";").strip()
            buffer.clear()
            _execute_and_print(conn, query)
        # else: keep accumulating lines

    buffer.clear()


def _execute_and_print(
    conn: DatabaseConnector, query: str
) -> None:
    """Execute *query* and pretty-print results."""
    try:
        rows, columns = conn.execute_query(query)
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ Error: {exc}\n")
        return

    if columns:
        print(tabulate(rows, headers=columns, tablefmt="psql"))
        count = len(rows)
        print(f"  ({count} row{'s' if count != 1 else ''} returned)\n")
    else:
        print("  ✓ Query executed successfully.\n")


def main() -> None:
    """Entry point for the CLI."""
    conn: Optional[DatabaseConnector] = None
    try:
        conn = _connect_interactive()
        _run_repl(conn)
    except Exception as exc:  # noqa: BLE001
        print(f"\n  ✗ Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn is not None:
            conn.disconnect()
            print("Disconnected. Bye!")


if __name__ == "__main__":
    main()
