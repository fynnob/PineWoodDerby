#!/usr/bin/env python3
import os
import socket
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, request

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "local_data"
DB_PATH = DATA_DIR / "derby_local.db"
UPLOAD_DIR = DATA_DIR / "uploads"

app = Flask(__name__, static_folder=str(ROOT), static_url_path="")


def _local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        sock.close()


def _query_one(sql: str, params: tuple = ()):  # simple helper
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


@app.get("/api/health")
def api_health():
    state = _query_one("SELECT id, current_round_id, current_heat_id, email_enabled FROM race_state WHERE id = 1")
    return jsonify({
        "ok": True,
        "mode": "local",
        "db": str(DB_PATH),
        "state": state,
        "local_ip": _local_ip(),
    })


@app.get("/api/local-info")
def api_local_info():
    return jsonify({
        "ssid": "PineWoodDerby",
        "local_url": f"http://{_local_ip()}:8000",
        "message": "Connect to PineWoodDerby and reload.",
    })


@app.get("/local-landing")
def local_landing():
    local_url = f"http://{_local_ip()}:8000"
    return f"""
<!doctype html>
<html>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>PineWoodDerby Local Mode</title></head>
<body style='font-family:system-ui;padding:24px;background:#0b1020;color:#f5f7ff;'>
  <h2 style='margin-top:0;'>PineWoodDerby Local Mode</h2>
  <p>Please connect to <strong>PineWoodDerby</strong> and reload this page.</p>
  <p>Local URL: <a style='color:#9db4ff;' href='{local_url}'>{local_url}</a></p>
  <script>
    fetch('{local_url}/api/health', {{ cache:'no-store' }})
      .then(r => r.ok ? location.href = '{local_url}' : null)
      .catch(() => null);
  </script>
</body>
</html>
"""


@app.post("/api/upload")
def api_upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "missing file"}), 400
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / file.filename
    file.save(path)
    return jsonify({"ok": True, "path": f"/local_data/uploads/{file.filename}"})


@app.get("/")
def root_page():
    return send_from_directory(ROOT, "index.html")


@app.get("/<path:path>")
def static_proxy(path: str):
    return send_from_directory(ROOT, path)


if __name__ == "__main__":
    host = os.getenv("PWD_LOCAL_HOST", "0.0.0.0")
    port = int(os.getenv("PWD_LOCAL_PORT", "8000"))
    app.run(host=host, port=port, debug=False)
