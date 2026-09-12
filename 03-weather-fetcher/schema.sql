CREATE TABLE IF NOT EXISTS weather_readings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    location_name  TEXT NOT NULL,
    latitude       REAL NOT NULL,
    longitude      REAL NOT NULL,
    temperature_c  REAL,
    humidity_pct   REAL,
    wind_speed_kmh REAL,
    weather_code   INTEGER,
    fetched_at     TEXT NOT NULL
);
