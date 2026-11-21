# Orphan configuration database cleanup

Run from `src/` after applying Configuration Discovery validation:

```sh
./wgd.sh cleanup-orphan-tables
./wgd.sh cleanup-orphan-tables --include-invalid
```

The default action is **preview only**. The command reads interface names from the `ConfigurationsInfo` table and from tables that match the WGDashboard peer schema. It compares them with `.conf` filenames from the configured `wg_conf_path` and `awg_conf_path` directories. It also validates the files with the same classifier used by Configuration Discovery.

- A missing `.conf` is an orphan candidate.
- A present but invalid/mismatched `.conf` is **protected** by default. Add `--include-invalid` to list it as a candidate. This can include non-WGDashboard configs such as WireProxy.
- A valid WG/AWG configuration always protects its database tables.
- All table suffixes (`_runtime`, `_restrict_access`, `_deleted`, `_transfer`, `_history_endpoint`) and the matching `ConfigurationsInfo` row are included in the preview and removed together.

Before performing deletion, **stop WGDashboard and make sure neither configuration directory is being modified**. Then run:

```sh
./wgd.sh cleanup-orphan-tables --apply --yes
# or, to also remove old data for unsupported .conf files:
./wgd.sh cleanup-orphan-tables --include-invalid --apply --yes
```

The command refuses to run when either configuration directory is unavailable, creates a timestamped SQLite backup using SQLite's backup API, and drops all selected tables and metadata in a single transaction. It does **not** remove any `.conf` file. To use a different SQLite file or paths, pass `--database`, `--config`, `--wg-dir`, or `--awg-dir`.

**Limitations:** only SQLite is supported. Database names that do not occur in `ConfigurationsInfo` and have no recognised peer-table schema are not automatically considered; this is deliberate to avoid deleting unrelated tables.
