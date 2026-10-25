#!/usr/bin/env python3
"""Move local peer state from interface tables to <interface>_runtime.

Run from src/ via `./wgd.sh migrate-runtime`, while WGDashboard is stopped.
Requires SQLite 3.35+ for DROP COLUMN.
"""

import argparse
import configparser
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import sys

RUNTIME_FIELDS = ("endpoint", "status", "latest_handshake")
PEER_MARKERS = {"id", "private_key", "allowed_ip", "total_receive", "total_sent"}
RUNTIME_COLUMNS = {"id", *RUNTIME_FIELDS}


class MigrationError(Exception):
    pass


def quote_identifier(value):
    return '"' + value.replace('"', '""') + '"'


def columns(connection, table):
    return {row[1] for row in connection.execute(
        f"PRAGMA table_info({quote_identifier(table)})"
    )}


def find_interfaces(connection, skipped=None):
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    existing = {row[0] for row in rows}
    # An empty unregistered peer table may be a leftover from legacy config discovery.
    registered = None
    if "ConfigurationsInfo" in existing:
        info_cols = columns(connection, "ConfigurationsInfo")
        if "ID" not in info_cols:
            raise MigrationError("ConfigurationsInfo: missing ID column")
        registered = {row[0] for row in connection.execute('SELECT "ID" FROM "ConfigurationsInfo"')}
    interfaces = []
    for (name,) in rows:
        if name.endswith(("_runtime", "_restrict_access", "_deleted", "_transfer", "_history_endpoint")):
            continue
        if not PEER_MARKERS.issubset(columns(connection, name)):
            continue
        if registered is not None and name not in registered:
            count = connection.execute(
                f"SELECT COUNT(*) FROM {quote_identifier(name)}"
            ).fetchone()[0]
            if count == 0:
                if skipped is not None:
                    skipped.append((name, "not in ConfigurationsInfo; 0 peers"))
                continue
            if skipped is not None:
                skipped.append((name, f"not in ConfigurationsInfo; {count} peers, preserved for migration"))
        main_columns = columns(connection, name)
        present = set(RUNTIME_FIELDS) & main_columns
        if present and present != set(RUNTIME_FIELDS):
            raise MigrationError(f"{name}: partially migrated main table (runtime fields {sorted(present)})")
        runtime = f"{name}_runtime"
        if runtime in existing:
            actual = columns(connection, runtime)
            if not RUNTIME_COLUMNS.issubset(actual):
                raise MigrationError(f"{runtime}: incompatible runtime table: {sorted(actual)}")
        elif not present:
            raise MigrationError(f"{name}: runtime fields already removed, but {runtime} is missing")
        interfaces.append(name)
    return interfaces


def migrate_interface(connection, name):
    main = quote_identifier(name)
    runtime_name = f"{name}_runtime"
    runtime = quote_identifier(runtime_name)
    if not (set(RUNTIME_FIELDS) & columns(connection, name)):
        # Schema is already converted. Verify no orphan or absent runtime rows.
        verify(connection, name)
        return False

    connection.execute(
        f"CREATE TABLE IF NOT EXISTS {runtime} ("
        '"id" VARCHAR(255) NOT NULL PRIMARY KEY, '
        '"endpoint" VARCHAR(255), "status" VARCHAR(255), '
        '"latest_handshake" VARCHAR(255))'
    )
    # If an earlier attempt populated some runtime values, we may continue only
    # when they agree with the authoritative old main-table values.
    mismatches = connection.execute(
        f"SELECT COUNT(*) FROM {main} AS p JOIN {runtime} AS r ON p.id = r.id "
        "WHERE NOT (p.endpoint IS r.endpoint) "
        "OR NOT (p.status IS r.status) "
        "OR NOT (p.latest_handshake IS r.latest_handshake)"
    ).fetchone()[0]
    if mismatches:
        raise MigrationError(f"{name}: {mismatches} existing runtime rows conflict with main data")
    orphans = connection.execute(
        f"SELECT COUNT(*) FROM {runtime} AS r LEFT JOIN {main} AS p ON p.id=r.id WHERE p.id IS NULL"
    ).fetchone()[0]
    if orphans:
        raise MigrationError(f"{runtime}: {orphans} orphan runtime rows")

    connection.execute(
        f"INSERT INTO {runtime} (id, endpoint, status, latest_handshake) "
        f"SELECT p.id, p.endpoint, p.status, p.latest_handshake FROM {main} AS p "
        f"WHERE NOT EXISTS (SELECT 1 FROM {runtime} AS r WHERE r.id=p.id)"
    )
    verify(connection, name, compare_values=True)
    for field in RUNTIME_FIELDS:
        connection.execute(f"ALTER TABLE {main} DROP COLUMN {quote_identifier(field)}")
    verify(connection, name)
    return True


def verify(connection, name, compare_values=False):
    main = quote_identifier(name)
    runtime = quote_identifier(f"{name}_runtime")
    missing = connection.execute(
        f"SELECT COUNT(*) FROM {main} AS p LEFT JOIN {runtime} AS r ON p.id=r.id WHERE r.id IS NULL"
    ).fetchone()[0]
    orphans = connection.execute(
        f"SELECT COUNT(*) FROM {runtime} AS r LEFT JOIN {main} AS p ON p.id=r.id WHERE p.id IS NULL"
    ).fetchone()[0]
    if missing or orphans:
        raise MigrationError(f"{name}: row mismatch (missing runtime={missing}, orphans={orphans})")
    if compare_values:
        diff = connection.execute(
            f"SELECT COUNT(*) FROM {main} AS p JOIN {runtime} AS r ON p.id=r.id "
            "WHERE NOT (p.endpoint IS r.endpoint) "
            "OR NOT (p.status IS r.status) "
            "OR NOT (p.latest_handshake IS r.latest_handshake)"
        ).fetchone()[0]
        if diff:
            raise MigrationError(f"{name}: {diff} migrated values differ")
    elif set(RUNTIME_FIELDS) & columns(connection, name):
        raise MigrationError(f"{name}: old runtime columns still present")


def backup_database(source):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = source.with_name(f"{source.name}.pre-peer-runtime-{stamp}.bak")
    with closing(sqlite3.connect(f"file:{source}?mode=rw", uri=True)) as conn:
        with closing(sqlite3.connect(target)) as backup:
            conn.backup(backup)
    return target


def migrate(path, *, dry_run=False, backup=True):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise MigrationError(f"SQLite database does not exist: {path}")
    if sqlite3.sqlite_version_info < (3, 35, 0):
        raise MigrationError(f"SQLite 3.35+ required; found {sqlite3.sqlite_version}")
    uri = f"file:{path}?mode=rw"
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as conn:
        warnings = []
        interfaces = find_interfaces(conn, warnings)
        pending = [name for name in interfaces if set(RUNTIME_FIELDS) & columns(conn, name)]
        for name in interfaces:
            if name not in pending:
                verify(conn, name)
        excluded = {name for name, reason in warnings if reason.endswith("0 peers")}
        if dry_run:
            already = [name for name in interfaces if name not in pending]
            print(f"Need migration ({len(pending)}):")
            for name in pending:
                print(f"  - {name}")
            print(f"Already migrated ({len(already)}):")
            for name in already:
                print(f"  - {name}")
            print(f"Skipped unregistered empty tables ({len(excluded)}):")
            for name in sorted(excluded):
                print(f"  - {name} (WARNING: not in ConfigurationsInfo; 0 peers)")
            for name, reason in warnings:
                if name not in excluded:
                    print(f"WARNING: {name}: {reason}")
        else:
            for name, reason in warnings:
                print(f"WARNING: {name}: {reason}")
        if not pending:
            print(f"No migration needed ({len(interfaces)} interface tables checked).")
            return 0
        if not dry_run:
            print(f"Interface tables to migrate ({len(pending)}):")
            for name in pending:
                print(f"  - {name}")
        if dry_run:
            print("Dry run: no changes made.")
            return len(pending)
    if backup:
        target = backup_database(path)
        print(f"Database backup: {target}")
    # One transaction covers every interface, including all DDL operations.
    with closing(sqlite3.connect(uri, uri=True, timeout=5, isolation_level=None)) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            interfaces = find_interfaces(conn)
            changed = sum(migrate_interface(conn, name) for name in interfaces)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    print(f"Migration completed: {changed} interface table(s).")
    return changed


def main(argv=None):
    default_db = Path(__file__).resolve().parents[1] / "db" / "wgdashboard.db"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=default_db,
                        help='SQLite DB file (default: src/db/wgdashboard.db)')
    parser.add_argument('--dry-run', action='store_true', help='Only list pending interface tables')
    parser.add_argument('--backup-dir', type=Path, default=Path('db'),
                        help='Directory for persistent external DB snapshots')
    args = parser.parse_args(argv)
    try:
        config = configparser.ConfigParser(strict=False)
        config.read('wg-dashboard.ini')
        backend = config.get('Database', 'type', fallback='sqlite').lower()
        if backend in ('mysql', 'postgresql'):
            from .migrate_peer_runtime_external import migrate_external
            migrate_external(dry_run=args.dry_run, backup_dir=args.backup_dir)
        elif backend == 'sqlite':
            migrate(args.database, dry_run=args.dry_run)
        else:
            raise MigrationError(f'Unsupported database type: {backend}')
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
