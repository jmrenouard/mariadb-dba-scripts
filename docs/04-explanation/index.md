# Explanation

Architectural background, design trade-offs, and safety guarantees behind `mariadb-dba-scripts`.

- [Backup, Retention, and Purge Mechanics](backup-retention-and-purge-mechanics.md): Understand LSN-based incremental chaining, `find -mindepth 1` retention guards, copytruncate trade-offs, and credential hygiene.
