#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETUP_PY = ROOT / "local_mode" / "setup.py"
SERVER_PY = ROOT / "local_mode" / "server.py"
VENV_PY = ROOT / "local_mode" / ".venv" / ("Scripts/python.exe" if sys.platform.startswith("win") else "bin/python")


def ensure_setup() -> None:
    db = ROOT / "local_data" / "derby_local.db"
    if db.exists() and VENV_PY.exists():
        return
    print("[run] Local runtime not ready, running setup first...")
    subprocess.check_call([sys.executable, str(SETUP_PY)])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PineWoodDerby in local mode")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--hotspot", action="store_true", help="Try to start PineWoodDerby Wi-Fi hotspot")
    args = parser.parse_args()

    ensure_setup()

    if args.hotspot:
        try:
            from .hotspot import start_hotspot
        except ImportError:
            from hotspot import start_hotspot
        ok, msg = start_hotspot("PineWoodDerby")
        print(f"[hotspot] {msg}")
        if not ok:
            print("[hotspot] continuing without blocking startup")

    env = os.environ.copy()
    env["PWD_LOCAL_HOST"] = args.host
    env["PWD_LOCAL_PORT"] = str(args.port)

    print("[run] Starting PineWoodDerby local server...")
    print(f"[run] URL: http://localhost:{args.port}")
    subprocess.check_call([str(VENV_PY), str(SERVER_PY)], env=env)


if __name__ == "__main__":
    main()
