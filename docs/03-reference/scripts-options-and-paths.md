# Scripts, Options, and Paths

## Script Inventory

| File | Interpreter | Purpose | External Binaries |
| :--- | :--- | :--- | :--- |
| [`.bash_profile`](../../.bash_profile) | Bash | Sample DBA environment profile and shell aliases | `mysql`, `nmon` |
| [`mysql_start.sh`](../../mysql_start.sh) | `/bin/sh` | Sample `mysqld_safe` startup command | `mysqld_safe` |
| [`mysql_stop.sh`](../../mysql_stop.sh) | `/bin/sh` | Sample `mysqladmin shutdown` command | `mysqladmin` |
| [`mysql_get_config.sh`](../../mysql_get_config.sh) | `/bin/bash` | Interactive discovery of OS info, `basedir`, socket, and credentials | `mysql`, `mysqladmin`, `mysqldump`, `netstat` |
| [`mariadb_backup.sh`](../../mariadb_backup.sh) | `/bin/bash` | Full, incremental, schema, binlog, engine, delete, and list runner | `mysql`, `mysqldump`, `mysqladmin`, `xtrabackup`, `rsync` |
| [`mariadb_log_purge.sh`](../../mariadb_log_purge.sh) | `/bin/bash` | Copy-and-truncate rotation for error and slow logs | `cp`, `find` |

## CLI Flags and Exit Codes

### `mariadb_backup.sh`

| Flag | Action | Requires Running MariaDB | Exit Codes |
| :--- | :--- | :--- | :--- |
| `--full` | Full XtraBackup snapshot + `--prepare --apply-log-only` | Yes | `0` on completion, `1` on failed pre-check |
| `--incre` | Incremental XtraBackup chained from highest `innodb_to_lsn` | Yes | `0` on completion, `1` on failed pre-check |
| `--schema` | Schema-only `mysqldump` (`-A --single-transaction --no-data --routines --events`) | Yes | `0` on completion, `1` on failed pre-check |
| `--binlog` | Copies `${LOGBIN_HOME}/` to `${BACKUP_HOME}/binary_backup` via `rsync -av` | Yes (pre-check) | `0` on completion, `1` on failed pre-check |
| `--engine` | Copies `ENGINE_HOME` and `XTRABACKUP_HOME` into `engine_backup_YYYYMMDDHHMM` | Yes (pre-check) | `0` on completion, `1` on failed pre-check |
| `--delete` | Deletes child directories in `BACKUP_HOME` and files in `binary_backup` older than `RESERVE_DAYS` | Yes (pre-check) | `0` on completion, `1` on failed pre-check |
| `--list` | Lists `xtrabackup_info`/`xtrabackup_checkpoints`, `binary_backup`, and `*_schema*` on disk | No | `0` if `BACKUP_HOME` exists, `1` otherwise |
| `--help`, `-h` | Prints usage text | No | `0` |
| Any other value | Prints usage text to standard error | No | `1` |

### `mariadb_log_purge.sh`

| Flag | Action | Exit Codes |
| :--- | :--- | :--- |
| `--err` | Copies `${ERROR_LOG_HOME}/${ERROR_LOG_NAME}` to `.YYYYMMDD_HH`, truncates active file to `0` bytes, scans for expired archives | `0` on completion, `1` if directory unwritable or source file missing |
| `--slow` | Copies `${SLOW_LOG_HOME}/${SLOW_LOG_NAME}` to `.YYYYMMDD_HH`, truncates active file to `0` bytes, scans for expired archives | `0` on completion, `1` if directory unwritable or source file missing |
| `--help`, `-h` | Prints usage text | `0` |
| Any other value | Prints usage text to standard error | `1` |

### `mysql_get_config.sh`

| Flag | Action | Exit Codes |
| :--- | :--- | :--- |
| *(none)* | Auto-detects OS, `basedir`, Unix socket, prompts when authentication fails, prints summary | `0` on completion, `1` on missing `basedir`, invalid socket, or unknown status |
| `--help`, `-h` | Prints usage summary | `0` |
| Any other value | Prints usage error to standard error | `1` |

## Environment Variables and Defaults

### `mariadb_backup.sh`

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DB_NAME` | `DBNAME` | Target MariaDB instance identifier |
| `MY_CNF` | `/engn001/masvc01/${DB_NAME}/my.cnf` | Server configuration file passed to `--defaults-file` |
| `RESERVE_DAYS` | `14` | Retention threshold in days (`-mtime +${RESERVE_DAYS}`) |
| `OS_USER` | `masvc01` | Operating system service account name |
| `DB_USER` | `bkupusr` | Database backup account |
| `DB_PWD` | *(empty string)* | Database backup password (supply via environment variable) |
| `SOCKET` | `/engn001/masvc01/${DB_NAME}/mysqld.sock` | MariaDB Unix socket path |
| `ENGINE_HOME` | `/engn001/masvc01/mariadb-10.0.28` | MariaDB installation prefix |
| `XTRABACKUP_HOME` | `/engn001/masvc01/percona-xtrabackup-2.4` | Percona XtraBackup installation prefix |
| `LOGBIN_HOME` | `/logs001/masvc01/${DB_NAME}/binary` | Source directory containing MariaDB binary logs |
| `BACKUP_HOME` | `/bkup001/masvc01/${DB_NAME}` | Root directory storing backup subdirectories |
| `LOG_HOME` | `/bkup001/masvc01/${DB_NAME}/backup_log` | Directory storing run logs and CSV history |
| `LOG_FILE` | `${LOG_HOME}/backup.db.YYYYMMDDHHMMSS.log` | Per-run log file path |
| `LOG_HISTORY` | `${LOG_HOME}/backup_all_history.log` | Append-only CSV backup history file |

### `mariadb_log_purge.sh`

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DB_NAME` | `LGUERP_PROD` | Instance identifier used in default log directory paths |
| `RESERVE_DAYS` | `4` | Days before old rotated log files match `find -mtime` |
| `ERROR_LOG_HOME` | `/logs001/masvc01/${DB_NAME}/error` | Error log directory |
| `ERROR_LOG_NAME` | `mysqld.err` | Active error log filename |
| `SLOW_LOG_HOME` | `/logs001/masvc01/${DB_NAME}/slow` | Slow query log directory |
| `SLOW_LOG_NAME` | `mysvc01-slow.log` | Active slow query log filename |

## Backup History CSV Schema

When `${LOG_HISTORY}` does not exist, `fn_write_history` writes the following header row:

```csv
DB_NAME,DB_USER,START_TIME,END_TIME,LAP_SECONDS,BACKUP_SIZE,BACKUP_TYPE,BACKUP_PATH,BACKUP_LOG
```
