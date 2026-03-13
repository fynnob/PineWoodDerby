#!/usr/bin/env python3
import json
import re
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = ROOT / "local_mode"
DATA_DIR = ROOT / "local_data"
VENV_DIR = LOCAL_DIR / ".venv"
DB_PATH = DATA_DIR / "derby_local.db"
SCHEMA_PATH = LOCAL_DIR / "schema.sql"
REQ_PATH = LOCAL_DIR / "requirements.txt"
CLOUD_TABLES = ["cars", "rounds", "heats", "heat_entries", "heat_results", "race_state"]


def venv_python() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if sys.platform.startswith("win") else "bin/python")


def ensure_venv() -> Path:
    py = venv_python()
    if py.exists():
        return py
    print("[setup] Creating local virtualenv...")
    venv.create(VENV_DIR, with_pip=True)
    return py


def install_deps(py_exe: Path) -> None:
    print("[setup] Installing Python dependencies in virtualenv...")
    subprocess.check_call([str(py_exe), "-m", "pip", "install", "-r", str(REQ_PATH)])


def read_cloud_config() -> tuple[str | None, str | None]:
    cfg = (ROOT / "config.js").read_text(encoding="utf-8")
    url_match = re.search(r"const\s+SUPABASE_URL\s*=\s*'([^']+)'", cfg)
    key_match = re.search(r"SUPABASE_ANON_KEY\s*=\s*\n\s*'([^']+)'\s*\+\s*\n\s*'([^']+)'\s*\+\s*\n\s*'([^']+)'", cfg)
    if not url_match or not key_match:
        return None, None
    return url_match.group(1), "".join(key_match.groups())


def download_supabase_table(url: str, key: str, table: str) -> list[dict]:
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}?select=*",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = resp.read().decode("utf-8")
        return json.loads(payload)


def import_cloud_data() -> None:
    url, key = read_cloud_config()
    if not url or not key:
        print("[setup] Skipping cloud import: could not parse Supabase config.")
        return

    print("[setup] Downloading current Supabase data into local DB...")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        for table in CLOUD_TABLES:
            try:
                rows = download_supabase_table(url, key, table)
            except urllib.error.URLError as exc:
                print(f"[setup] Cloud import skipped (network error on {table}): {exc}")
                conn.rollback()
                return
            except Exception as exc:
                print(f"[setup] Cloud import warning for {table}: {exc}")
                continue

            conn.execute(f"DELETE FROM {table}")
            if not rows:
                continue
            cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            valid_cols = [c for c in cols if c in rows[0].keys()]
            if not valid_cols:
                continue
            placeholders = ",".join(["?"] * len(valid_cols))
            sql = f"INSERT INTO {table} ({','.join(valid_cols)}) VALUES ({placeholders})"
            for row in rows:
                values = []
                for col in valid_cols:
                    v = row.get(col)
                    if isinstance(v, bool):
                        v = 1 if v else 0
                    values.append(v)
                conn.execute(sql, values)
            print(f"[setup] Imported {len(rows)} row(s) from {table}")

        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()


def init_db() -> None:
    print("[setup] Initializing SQLite database...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "uploads").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    print("=== PineWoodDerby Local Mode Setup ===")
    py_exe = ensure_venv()
    install_deps(py_exe)
    init_db()
    import_cloud_data()
    print("[setup] Done.")
    print(f"[setup] Database: {DB_PATH}")
    print("[setup] Next step: python3 run.py")


if __name__ == "__main__":
    main()
