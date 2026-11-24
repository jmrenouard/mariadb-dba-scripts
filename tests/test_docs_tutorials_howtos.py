"""Automated checks for mariadb-dba-scripts shell fixes, Diataxis docs, and labs."""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SHELL_SCRIPTS = (
    ".bash_profile",
    "mariadb_backup.sh",
    "mariadb_log_purge.sh",
    "mysql_get_config.sh",
    "mysql_start.sh",
    "mysql_stop.sh",
)
DIATAXIS_DIRS = (
    "01-tutorials",
    "02-how-to-guides",
    "03-reference",
    "04-explanation",
)
BOX_DRAWING_RE = re.compile(r"[\u2500-\u257f]")
HANGUL_RE = re.compile(r"[\uac00-\ud7af\u3130-\u318f]")
MERMAID_FENCE_RE = re.compile(r"^([ \t]*)```mermaid\s*$", re.MULTILINE)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)")


def _to_posix_path(path: pathlib.Path) -> str:
    """Convert a local filesystem path to a WSL-accessible POSIX path on Windows."""
    resolved = path.resolve()
    if sys.platform != "win32":
        return str(resolved)
    drive = resolved.drive.rstrip(":").lower()
    tail = resolved.as_posix().split(":", 1)[-1].lstrip("/")
    return f"/mnt/{drive}/{tail}"


def _run_bash(script_body: str) -> subprocess.CompletedProcess[str]:
    """Run a shell snippet in Linux bash directly or through WSL on Windows."""
    if sys.platform == "win32":
        wsl = shutil.which("wsl")
        if not wsl:
            raise unittest.SkipTest("WSL not available on Windows host")
        cmd = [wsl, "bash", "-s"]
    else:
        bash = shutil.which("bash")
        if not bash:
            raise unittest.SkipTest("bash not available on host")
        cmd = [bash, "-s"]
    raw = subprocess.run(
        cmd,
        input=script_body.replace("\r\n", "\n").encode("utf-8"),
        capture_output=True,
        check=False,
        timeout=30,
    )
    return subprocess.CompletedProcess(
        args=raw.args,
        returncode=raw.returncode,
        stdout=raw.stdout.decode("utf-8", errors="replace"),
        stderr=raw.stderr.decode("utf-8", errors="replace"),
    )


class TestScriptsAndDocs(unittest.TestCase):
    """Validate script correctness, sandbox execution, Diataxis structure, and Mermaid."""

    def test_shell_scripts_use_lf_line_endings(self) -> None:
        for name in SHELL_SCRIPTS:
            raw = (REPO_ROOT / name).read_bytes()
            self.assertNotIn(b"\r\n", raw, f"CRLF line ending found in {name}")

    def test_individual_bash_syntax_checks(self) -> None:
        repo_posix = _to_posix_path(REPO_ROOT)
        lines = [f'cd "{repo_posix}"']
        for name in SHELL_SCRIPTS:
            lines.append(f'bash -n "{name}"')
        res = _run_bash("\n".join(lines) + "\n")
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_cli_help_and_invalid_option_exits(self) -> None:
        repo_posix = _to_posix_path(REPO_ROOT)
        script = f"""
set -e
cd "{repo_posix}"
for flag in --help -h; do
  out_b=$(bash mariadb_backup.sh "$flag")
  echo "$out_b" | grep -q -- "--schema"
  echo "$out_b" | grep -q -- "--list"
  out_p=$(bash mariadb_log_purge.sh "$flag")
  echo "$out_p" | grep -q -- "--err"
  echo "$out_p" | grep -q -- "--slow"
  bash mysql_get_config.sh "$flag" | grep -q "Usage:"
done

set +e
bash mariadb_backup.sh --unknown-flag >/dev/null 2>&1
rc_b=$?
bash mariadb_log_purge.sh --unknown-flag >/dev/null 2>&1
rc_p=$?
bash mysql_get_config.sh --unknown-flag >/dev/null 2>&1
rc_c=$?
set -e
[ "$rc_b" -eq 1 ] && [ "$rc_p" -eq 1 ] && [ "$rc_c" -eq 1 ]
"""
        res = _run_bash(script)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_sandbox_log_purge_err_and_slow(self) -> None:
        repo_posix = _to_posix_path(REPO_ROOT)
        script = f"""
set -eu
SANDBOX=$(mktemp -d)
trap 'rm -rf "$SANDBOX"' EXIT

mkdir -p "$SANDBOX/err" "$SANDBOX/slow"
printf "line1\\nline2\\n" > "$SANDBOX/err/mysqld.err"
printf "# Time: 260101\\nSELECT 1;\\n" > "$SANDBOX/slow/mysvc01-slow.log"

cd "{repo_posix}"
ERROR_LOG_HOME="$SANDBOX/err" bash mariadb_log_purge.sh --err
SLOW_LOG_HOME="$SANDBOX/slow" bash mariadb_log_purge.sh --slow

# Active logs must be truncated to exactly 0 bytes (not 1-byte newline).
[ "$(wc -c < "$SANDBOX/err/mysqld.err")" -eq 0 ]
[ "$(wc -c < "$SANDBOX/slow/mysvc01-slow.log")" -eq 0 ]

# Hourly archive snapshots must keep original contents.
err_copy=$(find "$SANDBOX/err" -maxdepth 1 -name 'mysqld.err.*' | head -n1)
slow_copy=$(find "$SANDBOX/slow" -maxdepth 1 -name 'mysvc01-slow.log.*' | head -n1)
[ -n "$err_copy" ] && grep -q "line2" "$err_copy"
[ -n "$slow_copy" ] && grep -q "SELECT 1;" "$slow_copy"

# Missing log file returns exit code 1.
set +e
ERROR_LOG_HOME="$SANDBOX/err" ERROR_LOG_NAME="missing.err" bash mariadb_log_purge.sh --err >/dev/null 2>&1
rc_missing=$?
set -e
[ "$rc_missing" -eq 1 ]
"""
        res = _run_bash(script)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_sandbox_backup_list_schema_and_delete_mindepth_guard(self) -> None:
        repo_posix = _to_posix_path(REPO_ROOT)
        script = f"""
set -eu
SANDBOX=$(mktemp -d)
trap 'rm -rf "$SANDBOX"' EXIT

mkdir -p "$SANDBOX/bkup/DBNAME_full_20260101_0100"
mkdir -p "$SANDBOX/bkup/binary_backup"
mkdir -p "$SANDBOX/bkup/DBNAME_schema_20260101_0200"
mkdir -p "$SANDBOX/bkup/stale_dir"
mkdir -p "$SANDBOX/bin" "$SANDBOX/log"

cat <<'EOF' > "$SANDBOX/bkup/DBNAME_full_20260101_0100/xtrabackup_checkpoints"
backup_type = full-backuped
EOF

cat <<'EOF' > "$SANDBOX/bkup/DBNAME_full_20260101_0100/xtrabackup_info"
innodb_to_lsn = 1600000
start_time = 2026-01-01 01:00:01
end_time = 2026-01-01 01:00:09
partial = N
incremental = N
binlog_pos = filename 'mysql-bin.000001', position '320'
EOF

touch "$SANDBOX/bkup/binary_backup/mysql-bin.000001"
touch -d "20 days ago" "$SANDBOX/bkup/stale_dir"
touch -d "20 days ago" "$SANDBOX/bkup"

cat <<'EOF' > "$SANDBOX/bin/mock_mysqladmin"
#!/bin/sh
echo "Uptime: 100"
EOF
cat <<'EOF' > "$SANDBOX/bin/mock_mysql"
#!/bin/sh
cat >/dev/null
exit 0
EOF
cat <<'EOF' > "$SANDBOX/bin/mock_mysqldump"
#!/bin/sh
echo "-- mock schema ddl"
EOF
chmod +x "$SANDBOX/bin/mock_mysqladmin" "$SANDBOX/bin/mock_mysql" "$SANDBOX/bin/mock_mysqldump"

cd "{repo_posix}"

# 1. --list works cleanly without a running MySQL server.
list_out=$(DB_NAME="DBNAME" BACKUP_HOME="$SANDBOX/bkup" bash mariadb_backup.sh --list)
echo "$list_out" | grep -q "backup_type = full-backuped"
echo "$list_out" | grep -q "mysql-bin.000001"
echo "$list_out" | grep -q "DBNAME_schema_20260101_0200"

# 2. --schema writes DDL file while keeping BACKUP_HOME intact.
DB_NAME="DBNAME" \\
BACKUP_HOME="$SANDBOX/bkup" \\
LOG_HOME="$SANDBOX/log" \\
MYSQL="$SANDBOX/bin/mock_mysql" \\
MYSQLADMIN="$SANDBOX/bin/mock_mysqladmin" \\
MYSQLDUMP="$SANDBOX/bin/mock_mysqldump" \\
  bash mariadb_backup.sh --schema >/dev/null

schema_sql=$(find "$SANDBOX/bkup" -name "DBNAME_schema_*.sql" | head -n1)
[ -n "$schema_sql" ] && grep -q "mock schema ddl" "$schema_sql"

# 3. --delete deletes expired child dirs while preserving BACKUP_HOME itself even when old!
DB_NAME="DBNAME" \\
RESERVE_DAYS=14 \\
BACKUP_HOME="$SANDBOX/bkup" \\
LOG_HOME="$SANDBOX/log" \\
MYSQL="$SANDBOX/bin/mock_mysql" \\
MYSQLADMIN="$SANDBOX/bin/mock_mysqladmin" \\
  bash mariadb_backup.sh --delete >/dev/null

[ -d "$SANDBOX/bkup" ]
[ ! -d "$SANDBOX/bkup/stale_dir" ]
"""
        res = _run_bash(script)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_static_safety_regressions_fixed(self) -> None:
        backup_sh = (REPO_ROOT / "mariadb_backup.sh").read_text(encoding="utf-8")
        self.assertIn("-mindepth 1", backup_sh)
        self.assertNotIn("$LOGFILE", backup_sh)
        self.assertNotIn("//binary_backup", backup_sh)
        self.assertNotIn("bkupusr_password", backup_sh)

        config_sh = (REPO_ROOT / "mysql_get_config.sh").read_text(encoding="utf-8")
        self.assertNotIn('mysqldump="$mysqladmin', config_sh)
        self.assertIn('[ -n "$basedir" ] && [ -d "$basedir" ]', config_sh)
        self.assertNotIn("exit -1", config_sh)

    def test_diataxis_structure_links_and_english_purity(self) -> None:
        docs_dir = REPO_ROOT / "docs"
        self.assertTrue((docs_dir / "index.md").is_file())
        for sub in DIATAXIS_DIRS:
            sub_dir = docs_dir / sub
            self.assertTrue((sub_dir / "index.md").is_file(), f"Missing {sub}/index.md")
            md_files = list(sub_dir.glob("*.md"))
            self.assertGreaterEqual(len(md_files), 2, f"{sub} needs index.md plus guide(s)")

        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIsNone(HANGUL_RE.search(readme), "Korean text still present in README.md")
        self.assertNotIn("sh backup.sh", readme)
        self.assertNotIn("backupuser_password", readme)
        self.assertIn("mariadb_log_purge.sh", readme)
        self.assertIn("--schema", readme)

        for md in [REPO_ROOT / "README.md", *docs_dir.rglob("*.md")]:
            text = md.read_text(encoding="utf-8")
            self.assertIsNone(HANGUL_RE.search(text), f"Korean characters in {md}")
            for match in LINK_RE.finditer(text):
                target = match.group(1).strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (md.parent / target).resolve()
                self.assertTrue(
                    resolved.exists(),
                    f"Broken link {target!r} in {md.relative_to(REPO_ROOT)}",
                )

    def test_mermaid_column_zero_and_no_ascii_diagrams(self) -> None:
        md_files = [REPO_ROOT / "README.md", *(REPO_ROOT / "docs").rglob("*.md")]
        mermaid_count = 0
        for md in md_files:
            text = md.read_text(encoding="utf-8")
            self.assertIsNone(
                BOX_DRAWING_RE.search(text),
                f"ASCII box-drawing diagram character in {md.relative_to(REPO_ROOT)}",
            )
            for m in MERMAID_FENCE_RE.finditer(text):
                mermaid_count += 1
                self.assertEqual(
                    m.group(1),
                    "",
                    f"Indented mermaid fence in {md.relative_to(REPO_ROOT)}",
                )
        self.assertGreaterEqual(mermaid_count, 3)

    def test_ste_rules_on_how_to_guides(self) -> None:
        how_to_dir = REPO_ROOT / "docs" / "02-how-to-guides"
        for md in how_to_dir.glob("*.md"):
            lines = md.read_text(encoding="utf-8").splitlines()
            in_code = False
            for idx, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("```"):
                    in_code = not in_code
                    continue
                if in_code or not stripped or stripped.startswith("#"):
                    continue
                clean = re.sub(r"`[^`]+`", "CODE", stripped)
                clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
                self.assertNotIn(";", clean, f"Semicolon in STE guide {md.name}:{idx}")
                self.assertNotRegex(
                    clean.lower(),
                    r"\b(should|would|may|might|shall)\b",
                    f"Disallowed modal in {md.name}:{idx}",
                )
                for sentence in re.split(r"(?<=[.!?])\s+", clean):
                    words = [w for w in re.split(r"\s+", sentence.strip()) if w]
                    limit = 25 if stripped.startswith(("NOTE:", "CAUTION:", "WARNING:")) else 20
                    self.assertLessEqual(
                        len(words),
                        limit,
                        f"Sentence exceeds {limit} words in {md.name}:{idx}: {sentence}",
                    )


if __name__ == "__main__":
    unittest.main()
