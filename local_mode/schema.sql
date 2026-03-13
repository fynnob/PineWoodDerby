PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cars (
  id TEXT PRIMARY KEY,
  car_number INTEGER UNIQUE,
  kid_name TEXT NOT NULL,
  image_url TEXT,
  device_token TEXT NOT NULL,
  legal_status TEXT NOT NULL DEFAULT 'pending',
  eliminated INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rounds (
  id TEXT PRIMARY KEY,
  round_number INTEGER UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  advance_count INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS heats (
  id TEXT PRIMARY KEY,
  round_id TEXT NOT NULL,
  heat_number INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  UNIQUE(round_id, heat_number),
  FOREIGN KEY (round_id) REFERENCES rounds(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS heat_entries (
  id TEXT PRIMARY KEY,
  heat_id TEXT NOT NULL,
  lane_number INTEGER NOT NULL,
  car_id TEXT NOT NULL,
  UNIQUE(heat_id, lane_number),
  UNIQUE(heat_id, car_id),
  FOREIGN KEY (heat_id) REFERENCES heats(id) ON DELETE CASCADE,
  FOREIGN KEY (car_id) REFERENCES cars(id)
);

CREATE TABLE IF NOT EXISTS heat_results (
  id TEXT PRIMARY KEY,
  heat_id TEXT NOT NULL UNIQUE,
  first_place_car TEXT NOT NULL,
  second_place_car TEXT NOT NULL,
  third_place_car TEXT NOT NULL,
  fourth_place_car TEXT NOT NULL,
  entered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (heat_id) REFERENCES heats(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS race_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  current_round_id TEXT,
  current_heat_id TEXT,
  email_enabled INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO race_state (id, current_round_id, current_heat_id, email_enabled)
VALUES (1, NULL, NULL, 0);
