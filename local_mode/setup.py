#!/usr/bin/env python3
import sqlite3
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = ROOT / "local_mode"
DATA_DIR = ROOT / "local_data"
VENV_DIR = LOCAL_DIR / ".venv"
DB_PATH = DATA_DIR / "derby_local.db"
SCHEMA_PATH = LOCAL_DIR / "schema.sql"
REQ_PATH = LOCAL_DIR / "requirements.txt"


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
    print("[setup] Done.")
    print(f"[setup] Database: {DB_PATH}")
    print("[setup] Next step: python3 local_mode/run.py")


if __name__ == "__main__":
    main()
