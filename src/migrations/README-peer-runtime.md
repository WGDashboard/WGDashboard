# SQLite peer runtime migration

After updating WGDashboard to the version introducing `<interface>_runtime`, stop WGDashboard **before starting the updated application** and run from `src/`:

```sh
./wgd.sh migrate-runtime --dry-run
./wgd.sh migrate-runtime
```

The default database is `src/db/wgdashboard.db`. For a different location, add `--database /path/to/wgdashboard.db`. The command requires Python 3.12+ (as required by WGDashboard) and SQLite 3.35+.

The command creates a timestamped `*.bak` SQLite backup beside the original database **before altering any data**. Keep this backup somewhere safe. Every interface is migrated in one transaction: `endpoint`, `status`, and `latest_handshake` are copied into `<interface>_runtime`, checked, and then removed from the main peer table. Peer traffic counters and restricted/deleted/history tables are not changed.

A repeated run is safe. If an existing runtime row conflicts with the old main table, the command stops and rolls back without guessing which value is correct. Inspect the data before retrying.

**Backup compatibility:** SQL dumps created by an older WGDashboard version are not directly importable into the newer version. Restore with the original version first, then upgrade and run the migration.

This command migrates only SQLite; it does not change or migrate MySQL/PostgreSQL databases.
