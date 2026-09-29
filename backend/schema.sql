-- Connect to the database first: \c traffic_db

-- Stores raw readings from simulator (Student 1 writes here)
CREATE TABLE IF NOT EXISTS intersections (
    id          VARCHAR(10) PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Seed intersections (8 fake locations)
INSERT INTO intersections (id, name, latitude, longitude) VALUES
    ('IN_001', 'MG Road & Ring Road',       23.2599, 77.4126),
    ('IN_002', 'DB Mall Junction',           23.2354, 77.4307),
    ('IN_003', 'Arera Colony Crossing',      23.2196, 77.4352),
    ('IN_004', 'Hoshangabad Road Cross',     23.2054, 77.4167),
    ('IN_005', 'AIIMS Square',               23.1893, 77.4028),
    ('IN_006', 'Karond Junction',            23.2812, 77.3967),
    ('IN_007', 'Bhopal Talkies Cross',       23.2687, 77.4089),
    ('IN_008', 'Piplani Sector 9',           23.2421, 77.4598)
ON CONFLICT (id) DO NOTHING;

-- Raw sensor readings (Student 1 inserts here)
CREATE TABLE IF NOT EXISTS readings (
    id              SERIAL,
    intersection_id VARCHAR(10) REFERENCES intersections(id),
    timestamp       TIMESTAMP NOT NULL DEFAULT NOW(),
    vehicle_count   INTEGER NOT NULL,
    avg_speed_kmh   DOUBLE PRECISION NOT NULL,
    direction       VARCHAR(10) NOT NULL,
    CONSTRAINT readings_pkey PRIMARY KEY (id, timestamp)
);

-- Analysis results (YOU write here from analysis engine)
CREATE TABLE IF NOT EXISTS analysis_results (
    id              SERIAL PRIMARY KEY,
    intersection_id VARCHAR(10) REFERENCES intersections(id),
    computed_at     TIMESTAMP DEFAULT NOW(),
    congestion_level VARCHAR(10) NOT NULL,
    avg_speed_1min  DOUBLE PRECISION,
    vehicle_count_1min INTEGER,
    is_anomaly      BOOLEAN DEFAULT FALSE,
    anomaly_reason  VARCHAR(200)
);

-- Signal timing recommendations (YOU write here)
CREATE TABLE IF NOT EXISTS recommendations (
    id              SERIAL PRIMARY KEY,
    intersection_id VARCHAR(10) REFERENCES intersections(id),
    generated_at    TIMESTAMP DEFAULT NOW(),
    ns_green_secs   INTEGER NOT NULL,
    ew_green_secs   INTEGER NOT NULL,
    reason          VARCHAR(200)
);

-- Alerts log
CREATE TABLE IF NOT EXISTS alerts (
    id              SERIAL PRIMARY KEY,
    intersection_id VARCHAR(10) REFERENCES intersections(id),
    triggered_at    TIMESTAMP DEFAULT NOW(),
    severity        VARCHAR(10) NOT NULL,
    message         VARCHAR(300) NOT NULL,
    resolved        BOOLEAN DEFAULT FALSE
);