#!/usr/bin/env python3
"""Preview or remove orphan WGDashboard SQLite interface table families.

This is an offline maintenance command. Stop WGDashboard before --apply.
A present .conf protects its data by default, even if the file is invalid.
"""

import argparse
import configparser
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import sys

SUFFIXES = ("_runtime", "_restrict_access", "_transfer", "_deleted", "_history_endpoint")
PEER_MARKERS = {"id", "private_key", "allowed_ip", "total_receive", "total_sent"}


class CleanupError(Exception):
    pass


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def schema_tables(connection):
    return {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}


def table_columns(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA table_info({quote(table)})")}


def discover_candidates(connection):
    tables = schema_tables(connection)
    has_info = "ConfigurationsInfo" in tables
    metadata = set()
    if has_info:
        info_columns = table_columns(connection, "ConfigurationsInfo")
        if not {"ID", "Info"}.issubset(info_columns):
            raise CleanupError("ConfigurationsInfo has unexpected columns; refusing cleanup")
        metadata = {row[0] for row in connection.execute('SELECT "ID" FROM "ConfigurationsInfo"')}
    # Only tables with the peer schema count as an interface table. We also
    # consider ConfigurationsInfo IDs so a metadata-only orphan is visible.
    main = {
        name for name in tables
        if not name.endswith(SUFFIXES) and PEER_MARKERS.issubset(table_columns(connection, name))
    }
    candidates = main | metadata
    result = {}
    for name in sorted(candidates):
        family = sorted(t for t in (name, *(name + suffix for suffix in SUFFIXES)) if t in tables)
        if name in tables and name not in main:
            raise CleanupError(f"{name}: ConfigurationsInfo refers to a table with unexpected schema")
        # Metadata-only candidates can be cleaned too; they have no table family.
        result[name] = {"tables": family, "metadata": name in metadata}
    return result


def directory_paths(args):
    ini_path = args.config or Path(os.environ.get("CONFIGURATION_PATH", str(Path(__file__).resolve().parents[1]))) / "wg-dashboard.ini"
    ini = configparser.ConfigParser(interpolation=None)
    if (args.wg_dir is None or args.awg_dir is None):
        if not Path(ini_path).is_file():
            raise CleanupError(f"Missing configuration file: {ini_path} (or pass --wg-dir and --awg-dir)")
        ini.read(ini_path)
    wg = Path(args.wg_dir or ini.get("Server", "wg_conf_path", fallback="/etc/wireguard"))
    awg = Path(args.awg_dir or ini.get("Server", "awg_conf_path", fallback="/etc/amnezia/amneziawg"))
    for directory in (wg, awg):
        if not directory.is_dir():
            raise CleanupError(f"Configuration directory unavailable: {directory}. Refusing cleanup.")
    return wg, awg


def scan_disk(wg_dir, awg_dir):
    # Never assume an unreadable folder is empty.
    # The classification module is shared with live Configuration Discovery.
    from modules.ConfigurationDiscovery import detect_configuration_protocol
    present = set()
    invalid = {}
    locations = {}
    for protocol, directory in (("wg", wg_dir), ("awg", awg_dir)):
        try:
            paths = sorted(directory.iterdir())
        except OSError as exc:
            raise CleanupError(f"Cannot scan {directory}: {exc}") from exc
        for file in paths:
            if file.suffix != ".conf" or not file.is_file():
                continue
            name = file.stem
            if name in locations:
                raise CleanupError(f"Ambiguous configuration {name!r} in {locations[name]} and {file}")
            locations[name] = file
            present.add(name)
            detected, reason = detect_configuration_protocol(file)
            if detected != protocol:
                invalid[name] = reason or f"detected {detected}, expected {protocol}"
    return present, invalid


def backup_db(connection, database):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = database.with_name(f"{database.name}.pre-orphan-cleanup-{stamp}.bak")
    with closing(sqlite3.connect(destination)) as backup:
        connection.backup(backup)
    return destination


def cleanup(args):
    database = args.database.expanduser().resolve()
    if not database.is_file():
        raise CleanupError(f"Database does not exist: {database}")
    if args.yes and not args.apply:
        raise CleanupError("--yes requires --apply")
    if args.apply and not args.yes:
        raise CleanupError("Destructive operation requires --apply --yes")
    wg_dir, awg_dir = directory_paths(args)
    present, invalid = scan_disk(wg_dir, awg_dir)
    uri = database.as_uri() + "?mode=rw"
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as connection:
        candidates = discover_candidates(connection)
        # All existing filenames protect data unless the operator explicitly
        # opts into cleaning invalid/mismatched configs as well.
        protected = present - (set(invalid) if args.include_invalid else set())
        orphans = {name: item for name, item in candidates.items() if name not in protected}
        print(f"Database: {database}")
        print(f"WG configs: {wg_dir} | AWG configs: {awg_dir}")
        print(f"Known interfaces in DB: {len(candidates)}; protected files: {len(protected)}")
        if invalid:
            print("Unsupported configuration files:")
            for name, reason in sorted(invalid.items()):
                print(f"  - {name}: {reason}" + (" [eligible with --include-invalid]" if args.include_invalid else " [protected]"))
        if not orphans:
            print("No orphan interface tables or metadata rows found.")
            return 0
        print(f"Orphan candidates ({len(orphans)}):")
        for name, item in orphans.items():
            print(f"  - {name}")
            for table in item['tables']:
                print(f"      table: {table}")
            if item['metadata']:
                print("      ConfigurationsInfo row")
        if not args.apply:
            print("Preview only. Use --apply --yes while WGDashboard is stopped to remove these entries.")
            return len(orphans)
        backup = backup_db(connection, database)
        print(f"Database backup: {backup}")
        try:
            connection.execute("BEGIN IMMEDIATE")
            # Reevaluate the database after obtaining a write lock. File changes
            # between scan and apply remain an operational race; require offline use.
            current = discover_candidates(connection)
            if current != candidates:
                raise CleanupError("Database changed during cleanup; nothing removed")
            for name, item in orphans.items():
                for table in item['tables']:
                    connection.execute(f"DROP TABLE {quote(table)}")
                if item['metadata']:
                    connection.execute('DELETE FROM "ConfigurationsInfo" WHERE "ID" = ?', (name,))
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
    print(f"Cleanup complete: {len(orphans)} orphan interface(s) removed.")
    return len(orphans)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path(__file__).resolve().parents[1] / "db/wgdashboard.db")
    parser.add_argument("--config", type=Path, help="Path to wg-dashboard.ini")
    parser.add_argument("--wg-dir", type=Path, help="Override WireGuard configuration directory")
    parser.add_argument("--awg-dir", type=Path, help="Override AmneziaWG configuration directory")
    parser.add_argument("--include-invalid", action="store_true", help="Also consider existing but invalid/mismatched .conf files as orphaned")
    parser.add_argument("--apply", action="store_true", help="Perform removal (default: preview only)")
    parser.add_argument("--yes", action="store_true", help="Confirm destructive removal; only with --apply")
    args = parser.parse_args(argv)
    try:
        cleanup(args)
        return 0
    except (CleanupError, sqlite3.Error, OSError) as exc:
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
