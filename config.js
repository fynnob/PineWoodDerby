// Supabase project credentials — safe to commit, anon key only
const SUPABASE_URL = 'https://fixnbthycrvegkofvzfv.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  'eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZpeG5idGh5Y3J2ZWdrb2Z2emZ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIyOTQwMDcsImV4cCI6MjA4Nzg3MDAwN30.' +
  '4N67KwFK6WZwljLT7jQg_ubZJzEu5HgPd1X4DGDGEiY';

// Local Mode primitives (phase 1 scaffold)
const LOCAL_MODE_KEY = 'derby_local_mode';
const LOCAL_API_BASE = (typeof location !== 'undefined' && location.host)
  ? `${location.protocol}//${location.host}`
  : 'http://localhost:8000';

function isLocalMode() {
  try {
    return localStorage.getItem(LOCAL_MODE_KEY) === '1';
  } catch {
    return false;
  }
}

function _localBase() {
  return LOCAL_API_BASE.replace(/\/$/, '');
}

if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    if (isLocalMode()) {
      document.body.classList.add('is-local-mode');
    }
  });
}

async function _localFetchJson(path, options = {}) {
  const res = await fetch(_localBase() + path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    return { data: null, error: { message: body?.error?.message || body?.error || `HTTP ${res.status}` } };
  }
  return body;
}

class LocalQueryBuilder {
  constructor(client, table) {
    this.client = client;
    this.table = table;
    this.operation = 'select';
    this.selectExpr = '*';
    this.filters = [];
    this.orderBy = null;
    this.limitBy = null;
    this.values = null;
    this.patch = null;
    this.wantSingle = false;
    this.wantMaybeSingle = false;
    this.returning = false;
  }

  select(expr = '*') {
    this.selectExpr = expr;
    if (this.operation !== 'select') this.returning = true;
    return this;
  }

  insert(values) {
    this.operation = 'insert';
    this.values = values;
    return this;
  }

  update(patch) {
    this.operation = 'update';
    this.patch = patch;
    return this;
  }

  delete() {
    this.operation = 'delete';
    return this;
  }

  eq(column, value) { this.filters.push({ column, op: 'eq', value }); return this; }
  neq(column, value) { this.filters.push({ column, op: 'neq', value }); return this; }
  gt(column, value) { this.filters.push({ column, op: 'gt', value }); return this; }
  gte(column, value) { this.filters.push({ column, op: 'gte', value }); return this; }
  lt(column, value) { this.filters.push({ column, op: 'lt', value }); return this; }
  lte(column, value) { this.filters.push({ column, op: 'lte', value }); return this; }
  in(column, values) { this.filters.push({ column, op: 'in', value: values }); return this; }

  order(column, opts = {}) {
    this.orderBy = { column, ascending: opts.ascending !== false };
    return this;
  }

  limit(value) {
    this.limitBy = value;
    return this;
  }

  single() { this.wantSingle = true; return this; }
  maybeSingle() { this.wantMaybeSingle = true; return this; }

  async _exec() {
    const body = {
      table: this.table,
      operation: this.operation,
      select: this.selectExpr,
      filters: this.filters,
      order: this.orderBy,
      limit: this.limitBy,
      values: this.values,
      patch: this.patch,
      returning: this.returning,
    };
    const out = await _localFetchJson('/api/db/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (out.error) return out;

    if (!this.wantSingle && !this.wantMaybeSingle) return out;
    const list = Array.isArray(out.data) ? out.data : [];
    if (this.wantSingle) {
      if (list.length !== 1) {
        return { data: null, error: { message: `Expected single row, got ${list.length}` } };
      }
      return { data: list[0], error: null };
    }
    if (list.length === 0) return { data: null, error: null };
    if (list.length === 1) return { data: list[0], error: null };
    return { data: null, error: { message: `Expected 0 or 1 row, got ${list.length}` } };
  }

  then(resolve, reject) { return this._exec().then(resolve, reject); }
  catch(reject) { return this._exec().catch(reject); }
  finally(handler) { return this._exec().finally(handler); }
}

class LocalStorageBucket {
  constructor(bucket) { this.bucket = bucket; }

  async upload(path, file) {
    const fd = new FormData();
    fd.append('bucket', this.bucket);
    fd.append('path', path);
    fd.append('file', file);
    return _localFetchJson('/api/storage/upload', { method: 'POST', body: fd });
  }

  getPublicUrl(path) {
    return {
      data: {
        publicUrl: `${_localBase()}/api/storage/public/${encodeURIComponent(this.bucket)}/${path}`
      }
    };
  }

  async list(prefix = '', opts = {}) {
    const limit = opts?.limit ?? 100;
    const url = `/api/storage/list?bucket=${encodeURIComponent(this.bucket)}&prefix=${encodeURIComponent(prefix)}&limit=${encodeURIComponent(limit)}`;
    return _localFetchJson(url);
  }

  async remove(paths) {
    return _localFetchJson('/api/storage/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bucket: this.bucket, paths }),
    });
  }
}

class LocalChannel {
  constructor(name) {
    this.name = name;
    this.handlers = [];
    this.lastEventId = 0;
    this.lastDbVersion = -1;
    this._timer = null;
  }

  on(type, filter, callback) {
    this.handlers.push({ type, filter: filter || {}, callback });
    return this;
  }

  subscribe() {
    if (this._timer) return this;
    this._timer = setInterval(async () => {
      try {
        const out = await _localFetchJson(`/api/realtime/poll?since_event=${this.lastEventId}`);
        if (out.error) return;
        const dbVersion = out.dbVersion ?? this.lastDbVersion;
        const events = out.events || [];
        for (const ev of events) {
          this.lastEventId = Math.max(this.lastEventId, ev.id || 0);

          if (ev.channel === '__postgres_changes__') {
            for (const h of this.handlers) {
              if (h.type !== 'postgres_changes') continue;
              if (h.filter?.table && h.filter.table !== ev.payload.table) continue;
              if (h.filter?.event && h.filter.event !== '*' && h.filter.event !== ev.payload.type) continue;
              h.callback({
                eventType: ev.payload.type,
                new: ev.payload.new || {},
                old: ev.payload.old || {}
              });
            }
            continue;
          }

          if (ev.channel !== this.name) continue;
          for (const h of this.handlers) {
            if (h.type !== 'broadcast') continue;
            if (h.filter?.event && h.filter.event !== ev.event) continue;
            h.callback({ payload: ev.payload });
          }
        }

        this.lastDbVersion = dbVersion;
      } catch {
      }
    }, 900);
    return this;
  }

  async send(payload) {
    if (payload?.type !== 'broadcast') return { error: { message: 'Only broadcast is supported in local mode' } };
    return _localFetchJson('/api/realtime/broadcast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel: this.name, event: payload.event, payload: payload.payload || {} }),
    });
  }
}

function _createLocalClient() {
  return {
    from(table) { return new LocalQueryBuilder(this, table); },
    channel(name) { return new LocalChannel(name); },
    storage: {
      from(bucket) { return new LocalStorageBucket(bucket); }
    },
    functions: {
      invoke(name, opts = {}) {
        return _localFetchJson(`/api/functions/${encodeURIComponent(name)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(opts.body || {}),
        });
      }
    }
  };
}

let __derbyClient = null;
function createDerbyClient() {
  if (isLocalMode()) {
    if (!__derbyClient) __derbyClient = _createLocalClient();
    return __derbyClient;
  }
  return supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}
