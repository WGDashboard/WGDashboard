# Peer runtime database migration

WGDashboard automatically migrates existing peer tables when the updated application starts, **before configuration initialization**. No separate migration command is required. This applies to SQLite, MySQL/MariaDB, and PostgreSQL, including installations updated using an older updater.

The migration moves `endpoint`, `status`, and `latest_handshake` from each legacy peer table into a corresponding `<interface>_runtime` table, keyed by peer `id`. Other peer fields and the restricted, deleted, transfer, and endpoint-history tables are not intentionally changed.

## Before upgrading

Stop any other WGDashboard instances that share the database, and keep an independent database backup. Do not start the older WGDashboard version against a database that has already been migrated. The automatic migration is designed for a single application startup; concurrent migration processes are not supported.

## Selecting peer tables

The migrator identifies peer tables by their schema rather than interface-name prefixes. It uses `ConfigurationsInfo` when available:

- Registered peer tables with legacy runtime columns are migrated.
- Tables already using the new schema are verified and left unchanged.
- Empty, unregistered peer tables are skipped with a warning (for example, obsolete tables created for invalid configuration files).
- Unregistered peer tables containing peers are retained in the migration set with a warning, to avoid leaving saved peer data in an incompatible format.
- Inconsistent or partially migrated schemas cause migration to stop rather than silently discard data.

Skipping an empty unregistered table does **not** delete it. Ordinary non-peer application tables are not migration candidates.

## Backups and failure handling

- **SQLite:** creates a timestamped `wgdashboard.db.pre-peer-runtime-*.bak` beside the database before making changes. Schema changes for the selected interfaces run in one transaction; a failure rolls it back.
- **PostgreSQL:** creates a timestamped snapshot in `src/db/`; schema changes run in a transaction and are rolled back on failure.
- **MySQL/MariaDB:** creates a timestamped snapshot in `src/db/`. Since MySQL DDL is not fully transactional, the migrator attempts to restore the original peer tables from the snapshot if migration fails. An interruption may require manual recovery; an `in-progress` marker can prevent unsafe retries.

Backups and snapshots may contain peer private keys and other sensitive data. Protect them appropriately. If automatic migration fails, investigate the error and recover the database before restarting WGDashboard.

## Diagnostics

From the `src/` directory, with the relevant virtual environment installed and database configured in `wg-dashboard.ini`:

```sh
./venv/bin/python3 -m migrations.migrate_peer_runtime --dry-run
```

This lists tables needing migration, tables already migrated, and skipped empty unregistered tables **without changing the database**. An actual manual migration is still available for maintenance, but should only be run while WGDashboard is stopped:

```sh
./venv/bin/python3 -m migrations.migrate_peer_runtime
```

For SQLite, `--database /path/to/wgdashboard.db` selects a different database file; the default is `src/db/wgdashboard.db`. For external databases, connection settings come from `wg-dashboard.ini`, and `--backup-dir` selects the snapshot directory (default: `db`). SQLite requires version 3.35 or newer to drop columns.

## Restoring old backups

SQL dumps produced by older WGDashboard versions may not be directly importable into the new peer-table layout. Restore them using the original application version in an isolated environment, then upgrade and let the migration run. Do not run the old application against an already migrated production database.