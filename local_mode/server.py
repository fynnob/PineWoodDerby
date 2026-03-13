#!/usr/bin/env python3
import json
import os
import socket
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "local_data"
DB_PATH = DATA_DIR / "derby_local.db"
STORAGE_DIR = DATA_DIR / "storage"

DB_VERSION = 0
EVENT_ID = 0
EVENTS = []
EVENT_LOCK = Lock()
MAX_EVENTS = 300

BOOL_COLS = {"eliminated", "email_enabled"}

app = Flask(__name__)


def _local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        sock.close()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _to_row_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    out = dict(row)
    for key in BOOL_COLS:
        if key in out and out[key] is not None:
            out[key] = bool(out[key])
    return out


def _to_rows(rows) -> list[dict]:
    return [_to_row_dict(r) for r in rows]


def _table_cols(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _push_event(channel: str, event: str, payload: dict | None = None) -> None:
    global EVENT_ID
    with EVENT_LOCK:
        EVENT_ID += 1
        EVENTS.append({
            "id": EVENT_ID,
            "channel": channel,
            "event": event,
            "payload": payload or {},
        })
        if len(EVENTS) > MAX_EVENTS:
            del EVENTS[: len(EVENTS) - MAX_EVENTS]


def _touch_db() -> None:
    global DB_VERSION
    DB_VERSION += 1


def _normalize_value(value):
    if isinstance(value, bool):
        return 1 if value else 0
    return value


def _where_clause(filters: list[dict], table: str) -> tuple[str, list]:
    clauses = []
    params = []
    for filt in filters:
        col = filt.get("column")
        op = filt.get("op", "eq")
        val = filt.get("value")
        if table == "heat_results" and col == "heats.round_id":
            col = "h.round_id"
        elif "." in col:
            continue

        if op == "eq":
            clauses.append(f"{col} = ?")
            params.append(_normalize_value(val))
        elif op == "neq":
            clauses.append(f"{col} != ?")
            params.append(_normalize_value(val))
        elif op == "gt":
            clauses.append(f"{col} > ?")
            params.append(_normalize_value(val))
        elif op == "gte":
            clauses.append(f"{col} >= ?")
            params.append(_normalize_value(val))
        elif op == "lt":
            clauses.append(f"{col} < ?")
            params.append(_normalize_value(val))
        elif op == "lte":
            clauses.append(f"{col} <= ?")
            params.append(_normalize_value(val))
        elif op == "in":
            vals = val if isinstance(val, list) else []
            if not vals:
                clauses.append("1=0")
            else:
                placeholders = ",".join(["?"] * len(vals))
                clauses.append(f"{col} IN ({placeholders})")
                params.extend([_normalize_value(v) for v in vals])
    where_sql = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def _apply_relations(conn: sqlite3.Connection, table: str, select_expr: str, rows: list[dict]) -> list[dict]:
    if not rows:
        return rows

    if table == "race_state":
        with_rounds = "rounds(" in (select_expr or "")
        with_heats = "heats(" in (select_expr or "")
        with_nested_rounds = "heats(" in (select_expr or "") and "rounds(" in (select_expr or "")
        for row in rows:
            if with_rounds and row.get("current_round_id"):
                r = conn.execute("SELECT * FROM rounds WHERE id = ?", (row["current_round_id"],)).fetchone()
                row["rounds"] = _to_row_dict(r)
            if with_heats and row.get("current_heat_id"):
                h = conn.execute("SELECT * FROM heats WHERE id = ?", (row["current_heat_id"],)).fetchone()
                heat_obj = _to_row_dict(h)
                if with_nested_rounds and heat_obj and heat_obj.get("round_id"):
                    r = conn.execute("SELECT * FROM rounds WHERE id = ?", (heat_obj["round_id"],)).fetchone()
                    heat_obj["rounds"] = _to_row_dict(r)
                row["heats"] = heat_obj
        return rows

    if table == "heat_entries" and "cars(" in (select_expr or ""):
        ids = {r.get("car_id") for r in rows if r.get("car_id")}
        if ids:
            placeholders = ",".join(["?"] * len(ids))
            cars = conn.execute(f"SELECT * FROM cars WHERE id IN ({placeholders})", tuple(ids)).fetchall()
            car_map = {_to_row_dict(c)["id"]: _to_row_dict(c) for c in cars}
            for row in rows:
                row["cars"] = car_map.get(row.get("car_id"))
        return rows

    if table == "heat_results" and "heats!inner(" in (select_expr or ""):
        ids = {r.get("heat_id") for r in rows if r.get("heat_id")}
        if ids:
            placeholders = ",".join(["?"] * len(ids))
            heats = conn.execute(f"SELECT id, round_id FROM heats WHERE id IN ({placeholders})", tuple(ids)).fetchall()
            h_map = {h["id"]: {"round_id": h["round_id"]} for h in heats}
            for row in rows:
                row["heats"] = h_map.get(row.get("heat_id"), {"round_id": None})
        return rows

    return rows


def _select_rows(conn: sqlite3.Connection, table: str, select_expr: str, filters: list[dict], order: dict | None, limit: int | None) -> list[dict]:
    if table == "heat_results":
        where_sql, params = _where_clause(filters, table)
        sql = "SELECT hr.* FROM heat_results hr LEFT JOIN heats h ON h.id = hr.heat_id"
    else:
        where_sql, params = _where_clause(filters, table)
        sql = f"SELECT * FROM {table}"

    sql += where_sql
    if order and order.get("column"):
        col = order["column"]
        if "." in col:
            col = col.split(".")[-1]
        direction = "ASC" if order.get("ascending", True) else "DESC"
        sql += f" ORDER BY {col} {direction}"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)

    rows = _to_rows(conn.execute(sql, params).fetchall())
    return _apply_relations(conn, table, select_expr, rows)


@app.get("/api/health")
def api_health():
    conn = _connect()
    try:
        state = _to_row_dict(conn.execute("SELECT id, current_round_id, current_heat_id, email_enabled FROM race_state WHERE id = 1").fetchone())
    finally:
        conn.close()
    return jsonify({
        "ok": True,
        "mode": "local",
        "db": str(DB_PATH),
        "state": state,
        "local_ip": _local_ip(),
        "dbVersion": DB_VERSION,
    })


@app.get("/api/local-info")
def api_local_info():
    port = int(os.getenv("PWD_LOCAL_PORT", "8000"))
    return jsonify({
        "ssid": "PineWoodDerby",
        "local_url": f"http://{_local_ip()}:{port}",
        "message": "Connect to PineWoodDerby and reload.",
    })


@app.post("/api/db/query")
def api_db_query():
    payload = request.get_json(force=True, silent=True) or {}
    table = payload.get("table")
    op = payload.get("operation") or "select"
    select_expr = payload.get("select") or "*"
    filters = payload.get("filters") or []
    order = payload.get("order")
    limit = payload.get("limit")
    values = payload.get("values")
    patch = payload.get("patch") or {}
    returning = bool(payload.get("returning"))

    if not table:
        return jsonify({"data": None, "error": {"message": "Missing table"}}), 400

    conn = _connect()
    try:
        cols = _table_cols(conn, table)

        if op == "select":
            data = _select_rows(conn, table, select_expr, filters, order, limit)
            return jsonify({"data": data, "error": None})

        if op == "insert":
            rows = values if isinstance(values, list) else [values]
            inserted_ids = []
            for row in rows:
                row = dict(row or {})
                now = datetime.now(timezone.utc).isoformat()
                if "id" in cols and not row.get("id"):
                    row["id"] = str(uuid.uuid4())
                if table == "cars":
                    if not row.get("car_number"):
                        max_no = conn.execute("SELECT COALESCE(MAX(car_number), 0) FROM cars").fetchone()[0]
                        row["car_number"] = max_no + 1
                    row.setdefault("legal_status", "pending")
                    row.setdefault("eliminated", 0)
                    row.setdefault("created_at", now)
                if table == "rounds":
                    row.setdefault("status", "pending")
                    row.setdefault("created_at", now)
                if table == "heats":
                    row.setdefault("status", "pending")
                if table == "race_state":
                    row.setdefault("updated_at", now)

                write_row = {k: _normalize_value(v) for k, v in row.items() if k in cols}
                keys = list(write_row.keys())
                placeholders = ",".join(["?"] * len(keys))
                conn.execute(
                    f"INSERT INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
                    [write_row[k] for k in keys],
                )
                if "id" in write_row:
                    inserted_ids.append(write_row["id"])
            conn.commit()
            _touch_db()
            if returning and inserted_ids:
                placeholders = ",".join(["?"] * len(inserted_ids))
                out = _to_rows(conn.execute(f"SELECT * FROM {table} WHERE id IN ({placeholders})", inserted_ids).fetchall())
                out = _apply_relations(conn, table, select_expr, out)
                return jsonify({"data": out, "error": None})
            return jsonify({"data": None, "error": None})

        if op == "update":
            where_sql, params = _where_clause(filters, table)
            write_patch = {k: _normalize_value(v) for k, v in patch.items() if k in cols}
            if not write_patch:
                return jsonify({"data": None, "error": None})
            assignments = ", ".join([f"{k} = ?" for k in write_patch.keys()])
            update_params = list(write_patch.values()) + params
            if returning:
                before = _select_rows(conn, table, select_expr, filters, None, None)
                before_ids = [r.get("id") for r in before if r.get("id")]
            conn.execute(f"UPDATE {table} SET {assignments}{where_sql}", update_params)
            conn.commit()
            _touch_db()
            if returning:
                if not before_ids:
                    return jsonify({"data": [], "error": None})
                placeholders = ",".join(["?"] * len(before_ids))
                out = _to_rows(conn.execute(f"SELECT * FROM {table} WHERE id IN ({placeholders})", before_ids).fetchall())
                out = _apply_relations(conn, table, select_expr, out)
                return jsonify({"data": out, "error": None})
            return jsonify({"data": None, "error": None})

        if op == "delete":
            where_sql, params = _where_clause(filters, table)
            deleted = _select_rows(conn, table, select_expr, filters, None, None) if returning else None
            conn.execute(f"DELETE FROM {table}{where_sql}", params)
            conn.commit()
            _touch_db()
            return jsonify({"data": deleted if returning else None, "error": None})

        return jsonify({"data": None, "error": {"message": f"Unsupported operation: {op}"}}), 400
    except Exception as exc:
        return jsonify({"data": None, "error": {"message": str(exc)}}), 500
    finally:
        conn.close()


@app.post("/api/storage/upload")
def api_storage_upload():
    bucket = request.form.get("bucket", "")
    path = request.form.get("path", "")
    file = request.files.get("file")
    if not bucket or not path or not file:
        return jsonify({"data": None, "error": {"message": "bucket, path and file are required"}}), 400

    target = STORAGE_DIR / bucket / path
    target.parent.mkdir(parents=True, exist_ok=True)
    file.save(target)
    _touch_db()
    return jsonify({"data": {"path": path}, "error": None})


@app.get("/api/storage/list")
def api_storage_list():
    bucket = request.args.get("bucket", "")
    prefix = request.args.get("prefix", "")
    limit = int(request.args.get("limit", "100"))
    if not bucket:
        return jsonify({"data": None, "error": {"message": "bucket required"}}), 400

    base = (STORAGE_DIR / bucket)
    base.mkdir(parents=True, exist_ok=True)
    search = base / prefix if prefix else base
    files = []
    if search.exists():
        for p in search.rglob("*"):
            if p.is_file():
                rel = p.relative_to(base).as_posix()
                files.append({"name": rel, "created_at": datetime.fromtimestamp(p.stat().st_ctime).isoformat()})
    files.sort(key=lambda f: f["created_at"], reverse=True)
    return jsonify({"data": files[:limit], "error": None})


@app.post("/api/storage/remove")
def api_storage_remove():
    payload = request.get_json(force=True, silent=True) or {}
    bucket = payload.get("bucket", "")
    paths = payload.get("paths") or []
    if not bucket:
        return jsonify({"data": None, "error": {"message": "bucket required"}}), 400
    removed = []
    for rel in paths:
        p = STORAGE_DIR / bucket / rel
        if p.exists() and p.is_file():
            p.unlink()
            removed.append(rel)
    if removed:
        _touch_db()
    return jsonify({"data": removed, "error": None})


@app.get("/api/storage/public/<bucket>/<path:obj_path>")
def api_storage_public(bucket: str, obj_path: str):
    return send_from_directory(STORAGE_DIR / bucket, obj_path)


@app.post("/api/functions/<name>")
def api_function_invoke(name: str):
    if name == "send-registration-email":
        return jsonify({"data": {"ok": True, "local": True, "message": "Email skipped in local mode"}, "error": None})
    return jsonify({"data": None, "error": {"message": f"Function not available in local mode: {name}"}}), 404


@app.post("/api/realtime/broadcast")
def api_realtime_broadcast():
    payload = request.get_json(force=True, silent=True) or {}
    channel = payload.get("channel")
    event = payload.get("event")
    body = payload.get("payload") or {}
    if not channel or not event:
        return jsonify({"ok": False, "error": "channel and event required"}), 400
    _push_event(channel, event, body)
    return jsonify({"ok": True, "eventId": EVENT_ID})


@app.get("/api/realtime/poll")
def api_realtime_poll():
    since_event = int(request.args.get("since_event", "0"))
    with EVENT_LOCK:
        events = [e for e in EVENTS if e["id"] > since_event]
    return jsonify({
        "dbVersion": DB_VERSION,
        "lastEventId": EVENT_ID,
        "events": events,
    })


@app.get("/local-landing")
def local_landing():
    port = int(os.getenv("PWD_LOCAL_PORT", "8000"))
    local_url = f"http://{_local_ip()}:{port}"
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


@app.get("/")
def root_page():
    return send_from_directory(ROOT, "index.html")


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def static_proxy(path: str):
    if not path or path.endswith("/"):
        path += "index.html"
    
    full_path = ROOT / path
    if full_path.is_dir():
        path += "/index.html"
        
    return send_from_directory(str(ROOT), path)


if __name__ == "__main__":
    host = os.getenv("PWD_LOCAL_HOST", "0.0.0.0")
    port = int(os.getenv("PWD_LOCAL_PORT", "8000"))
    app.run(host=host, port=port, debug=False)
