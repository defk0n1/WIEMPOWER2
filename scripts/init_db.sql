-- Create tables for irrigation monitoring system

-- Sensor readings table
CREATE TABLE IF NOT EXISTS sensor_readings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    zone_id VARCHAR(50) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,
    value FLOAT NOT NULL,
    unit VARCHAR(20),
    depth_cm INTEGER
);

-- Irrigation events table
CREATE TABLE IF NOT EXISTS irrigation_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    zone_id VARCHAR(50) NOT NULL,
    amount_mm FLOAT NOT NULL,
    manual BOOLEAN DEFAULT FALSE
);

-- Soil analysis table
CREATE TABLE IF NOT EXISTS soil_analysis (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    zone_id VARCHAR(50) NOT NULL,
    moisture_pct FLOAT,
    paw_percentage FLOAT,
    field_capacity FLOAT,
    wilting_point FLOAT,
    status VARCHAR(50),
    irrigation_needed BOOLEAN,
    predicted_days_to_threshold FLOAT,
    current_moisture FLOAT
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_sensor_readings_zone_time ON sensor_readings(zone_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_irrigation_events_zone_time ON irrigation_events(zone_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_soil_analysis_zone_time ON soil_analysis(zone_id, timestamp DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO irrigation_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO irrigation_user;