# Tutorial: Backup Discovery and Log Rotation Lab

In this lab you test syntax, inspect CLI options, simulate a backup tree, and run safe log rotation inside `/tmp/mariadb-dba-lab` without touching any production database.

## Prerequisites

- Bash (`bash`) and standard core utilities (`find`, `mkdir`, `cp`, `sort`)
- A local clone of `mariadb-dba-scripts`

## Step 1: Verify Script Syntax and Help Output

Run `bash -n` on every script to confirm valid syntax before executing anything:

```bash
for script in mariadb_backup.sh mariadb_log_purge.sh mysql_get_config.sh mysql_start.sh mysql_stop.sh .bash_profile; do
  bash -n "$script" && echo "SYNTAX_OK: $script"
done
```

Expected output:

```text
SYNTAX_OK: mariadb_backup.sh
SYNTAX_OK: mariadb_log_purge.sh
SYNTAX_OK: mysql_get_config.sh
SYNTAX_OK: mysql_start.sh
SYNTAX_OK: mysql_stop.sh
SYNTAX_OK: .bash_profile
```

Inspect the supported flags for each CLI script:

```bash
bash mariadb_backup.sh --help
bash mariadb_log_purge.sh --help
bash mysql_get_config.sh --help
```

Confirm that passing an unknown argument fails cleanly with exit status `1`:

```bash
bash mariadb_backup.sh --invalid-flag ; echo "exit=$?"
bash mariadb_log_purge.sh --invalid-flag ; echo "exit=$?"
```

Both commands print usage text to standard error and output `exit=1`.

## Step 2: Simulate On-Disk Backups and Run `--list`

Create an isolated sandbox directory containing mock XtraBackup metadata, a binary log copy, and a schema backup directory:

```bash
LAB_DIR="/tmp/mariadb-dba-lab"
rm -rf "${LAB_DIR}"
mkdir -p "${LAB_DIR}/bkup/DBNAME_full_20260101_0100"
mkdir -p "${LAB_DIR}/bkup/binary_backup"
mkdir -p "${LAB_DIR}/bkup/DBNAME_schema_20260101_0200"

cat <<'EOF' > "${LAB_DIR}/bkup/DBNAME_full_20260101_0100/xtrabackup_checkpoints"
backup_type = full-backuped
EOF

cat <<'EOF' > "${LAB_DIR}/bkup/DBNAME_full_20260101_0100/xtrabackup_info"
innodb_to_lsn = 1600000
start_time = 2026-01-01 01:00:01
end_time = 2026-01-01 01:00:09
partial = N
incremental = N
binlog_pos = filename 'mysql-bin.000001', position '320'
EOF

touch "${LAB_DIR}/bkup/binary_backup/mysql-bin.000001"
```

Run `--list` against the sandboxed `BACKUP_HOME`:

```bash
DB_NAME="DBNAME" BACKUP_HOME="${LAB_DIR}/bkup" bash mariadb_backup.sh --list
```

Expected output lists the `xtrabackup_checkpoints` type, `innodb_to_lsn` metadata, `mysql-bin.000001` under `binary_backup`, and `DBNAME_schema_20260101_0200`.

## Step 3: Run Sandboxed Log Rotation (`--err` and `--slow`)

Create sample active error and slow query log files inside `${LAB_DIR}`:

```bash
mkdir -p "${LAB_DIR}/logs/error" "${LAB_DIR}/logs/slow"
printf "2026-01-01 Note: server started\n" > "${LAB_DIR}/logs/error/mysqld.err"
printf "# Time: 260101  2:00:00\nSELECT 1;\n" > "${LAB_DIR}/logs/slow/mysvc01-slow.log"
```

Execute `mariadb_log_purge.sh` with overridden directory variables:

```bash
ERROR_LOG_HOME="${LAB_DIR}/logs/error" bash mariadb_log_purge.sh --err
SLOW_LOG_HOME="${LAB_DIR}/logs/slow" bash mariadb_log_purge.sh --slow
```

Verify that both active log files are truncated to `0` bytes while timestamped hourly copies remain in place:

```bash
ls -la "${LAB_DIR}/logs/error" "${LAB_DIR}/logs/slow"
```

Both `mysqld.err` and `mysvc01-slow.log` now report size `0`, alongside `mysqld.err.YYYYMMDD_HH` and `mysvc01-slow.log.YYYYMMDD_HH`.

## Step 4: Clean Up the Lab

```bash
rm -rf "${LAB_DIR}"
```

Next, read the [How-To Guides](../02-how-to-guides/index.md) for production procedures or [Explanation](../04-explanation/backup-retention-and-purge-mechanics.md) to understand how LSN selection and copytruncate rotation work.
