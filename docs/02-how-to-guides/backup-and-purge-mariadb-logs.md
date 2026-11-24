# Back Up MariaDB and Rotate Logs

Use this procedure to run `mariadb_backup.sh` and `mariadb_log_purge.sh` on a Linux host.

## Prerequisites

- Verify `bash` and `find` are installed on the host.
- Confirm MariaDB and Percona XtraBackup paths exist for `ENGINE_HOME` and `XTRABACKUP_HOME`.
- Obtain valid backup database credentials before you export `DB_PWD`.
- See [Scripts, Options, and Paths](../03-reference/scripts-options-and-paths.md) for variable defaults.

## Check CLI Options and Syntax

1. Open the repository directory.
2. Run syntax checks on all scripts before execution:

```bash
for script in mariadb_backup.sh mariadb_log_purge.sh mysql_get_config.sh mysql_start.sh mysql_stop.sh .bash_profile; do
  bash -n "$script"
done
```

3. Run help commands to confirm valid CLI options:

```bash
bash mariadb_backup.sh --help
bash mariadb_log_purge.sh --help
```

## Configure Environment Variables

CAUTION: Do not store plain passwords in script files. Export `DB_PWD` in the shell environment before script execution.

1. Set the target database variables in your shell session:

```bash
export DB_NAME="DBNAME"
export DB_USER="bkupusr"
export DB_PWD="replace_with_secret"
export BACKUP_HOME="/bkup001/masvc01/${DB_NAME}"
export LOG_HOME="${BACKUP_HOME}/backup_log"
```

2. If `BACKUP_HOME` does not exist, create it and grant write permission to the service user:

```bash
mkdir -p "${BACKUP_HOME}" "${LOG_HOME}"
```

## Run Backup Jobs

1. Run a full XtraBackup snapshot first:

```bash
bash mariadb_backup.sh --full
```

2. Run an incremental backup after new database writes occur:

```bash
bash mariadb_backup.sh --incre
```

3. Run a schema dump when you want DDL definitions without table rows:

```bash
bash mariadb_backup.sh --schema
```

4. Run a binary log sync to copy logs from `LOGBIN_HOME`:

```bash
bash mariadb_backup.sh --binlog
```

5. Run an engine backup when you update MariaDB or XtraBackup binaries:

```bash
bash mariadb_backup.sh --engine
```

NOTE: The `--full`, `--incre`, `--schema`, `--binlog`, and `--engine` flags require a live MariaDB server.

## Purge Old Backups Safely

CAUTION: Confirm `BACKUP_HOME` and `RESERVE_DAYS` before deletion. Wrong path values remove data directories inside `BACKUP_HOME`.

1. Verify `RESERVE_DAYS` is at least `1` and inspect current directories:

```bash
echo "BACKUP_HOME=${BACKUP_HOME} RESERVE_DAYS=${RESERVE_DAYS:-14}"
bash mariadb_backup.sh --list
```

2. Run retention cleanup on expired directories and binary logs:

```bash
bash mariadb_backup.sh --delete
```

## Rotate Error and Slow Logs

1. Set `ERROR_LOG_HOME` and `SLOW_LOG_HOME` to match your MariaDB log directories.
2. If you rotate the error log, run `--err`:

```bash
bash mariadb_log_purge.sh --err
```

3. If you rotate the slow query log, run `--slow`:

```bash
bash mariadb_log_purge.sh --slow
```

NOTE: `mariadb_log_purge.sh` creates an hourly copy, truncates the active log file, and prints candidate files older than `RESERVE_DAYS`.

## Validate Results

1. List backups on disk to verify snapshot directories and metadata:

```bash
bash mariadb_backup.sh --list
```

2. Inspect `${LOG_HOME}/backup_all_history.log` for recent completion records.
3. Confirm the active error log and slow log have size zero immediately after rotation.

## Rollback

1. If `--err` or `--slow` rotated an active log early, inspect the timestamped hourly archive file.
2. Never edit files inside `BACKUP_HOME` during a restore.
3. Stage recovery files in a separate restore directory first.
4. Read [Backup Retention and Purge Mechanics](../04-explanation/backup-retention-and-purge-mechanics.md) to plan full and incremental restore steps.
