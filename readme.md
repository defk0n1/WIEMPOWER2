# 🌱 WIEMPOWER2 - IoT Irrigation Monitoring & Prediction System

**Advanced Docker-based solution for smart agriculture with NPK monitoring, ML-powered irrigation decisions, and real-time analytics**

Built by: **defk0n1**  
Last Updated: **2025-11-02**

---

## 📖 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Services](#-services)
- [IoT Sensor Integration](#-iot-sensor-integration)
- [API Documentation](#-api-documentation)
- [Development](#-development)
- [Useful Commands](#-useful-commands)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

---

## 🎯 Overview

WIEMPOWER2 is a comprehensive IoT-based irrigation monitoring and control system designed for precision agriculture. It combines real-time sensor data collection, machine learning-powered decision making, and automated irrigation control to optimize water usage and crop yields.

### Key Capabilities

- **Real-time Monitoring**: Track soil moisture, temperature, humidity, NPK nutrients, and water levels
- **Intelligent Irrigation**: ML-powered pump control based on environmental conditions
- **Nutrient Management**: Automated NPK (Nitrogen, Phosphorus, Potassium) monitoring and fertilization recommendations
- **Water Management**: Track water reservoir levels with automated alerts
- **Data Analytics**: Historical data visualization and trend analysis via Streamlit dashboard
- **Automated Scheduling**: Periodic irrigation jobs with configurable intervals
- **Weather Integration**: 7-day weather forecasting for irrigation planning

---

## 🏗️ System Architecture

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        IoT Sensors Layer                         │
│  (Soil Moisture, NPK, Temperature, Humidity, Water Level, etc.)  │
└────────────────────┬────────────────────────────────────────────┘
                     │ MQTT Protocol
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│               MQTT Broker (Eclipse Mosquitto)                    │
│                    Port 1883 (MQTT), 9001 (WebSocket)           │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ├──────────→ ┌────────────────────────────────────────┐
       │            │   Main Application (main.py)           │
       │            │  - MQTT Consumer                        │
       │            │  - Soil Analyzer (farmingpy)           │
       │            │  - NPK Analyzer                        │
       │            │  - Irrigation Controller               │
       │            │  - Automated Irrigation Jobs           │
       │            └──────────┬─────────────────────────────┘
       │                       │
       ├──────────→ ┌──────────┴─────────────────────────────┐
       │            │  PostgreSQL Database                    │
       │            │  - Sensor readings (time-series)       │
       │            │  - NPK levels                          │
       │            │  - Irrigation events                   │
       │            │  - Water level history                 │
       │            │  Port 5432                             │
       │            └──────────┬─────────────────────────────┘
       │                       │
       ├──────────→ ┌──────────┴─────────────────────────────┐
       │            │  ML Service (XGBoost)                   │
       │            │  - Pump activation predictions         │
       │            │  - Flask API                           │
       │            │  Port 8000                             │
       │            └────────────────────────────────────────┘
       │
       ├──────────→ ┌────────────────────────────────────────┐
       │            │  Scheduler API (FastAPI)               │
       │            │  - Weather forecasting (Open-Meteo)    │
       │            │  - LLM-based irrigation scheduling     │
       │            │  Port 5002                             │
       │            └────────────────────────────────────────┘
       │
       └──────────→ ┌────────────────────────────────────────┐
                    │  Streamlit Dashboard                    │
                    │  - Real-time data visualization        │
                    │  - NPK status monitoring               │
                    │  - Historical trends                   │
                    │  Port 8501                             │
                    └────────────────────────────────────────┘
```

### Data Flow

1. **Sensor Data Collection**: IoT sensors publish data to MQTT topics
2. **Data Processing**: Main application consumes MQTT messages and processes data
3. **Analysis**: 
   - Soil moisture analyzed using farmingpy library
   - NPK levels evaluated against crop-specific thresholds
   - Water levels monitored for reservoir management
4. **Decision Making**: 
   - ML model predicts optimal pump activation
   - Rule-based irrigation controller makes real-time decisions
5. **Storage**: All data persisted to PostgreSQL for historical analysis
6. **Visualization**: Streamlit dashboard queries database for real-time displays
7. **Automation**: Scheduled jobs run periodically for proactive irrigation

---

## ✨ Features

### Sensor Monitoring
- ✅ **Soil Moisture** - Multi-depth monitoring with PAW (Plant Available Water) calculation
- ✅ **NPK Nutrients** - Real-time nitrogen, phosphorus, and potassium level tracking
- ✅ **Temperature** - Soil and air temperature monitoring
- ✅ **Humidity** - Air humidity with heat index and dew point calculation
- ✅ **Water Level** - Reservoir capacity monitoring with low-level alerts
- ✅ **Rainfall** - Precipitation tracking for irrigation adjustment

### Intelligent Control
- ✅ **ML-Powered Irrigation** - XGBoost model for pump activation decisions
- ✅ **Automated Fertilization** - NPK-based fertilizer recommendations
- ✅ **Scheduled Jobs** - Configurable periodic irrigation analysis
- ✅ **Real-time Alerts** - Critical moisture and nutrient level warnings
- ✅ **Weather Forecasting** - 7-day weather prediction for planning

### Data & Analytics
- ✅ **PostgreSQL Storage** - Time-series data persistence
- ✅ **Streamlit Dashboard** - Interactive web-based visualization
- ✅ **Historical Trends** - Long-term data analysis and reporting
- ✅ **Multi-zone Support** - Independent monitoring per field zone

### Integration
- ✅ **MQTT Protocol** - Standard IoT communication
- ✅ **RESTful APIs** - ML service and scheduler endpoints
- ✅ **Docker Deployment** - Containerized microservices
- ✅ **Mock Data Generator** - Built-in sensor simulation for testing

---

## 🛠️ Technology Stack

### Backend
- **Python 3.10** - Core application language
- **Paho MQTT** - MQTT client library
- **SQLAlchemy** - ORM for database operations
- **Farmingpy** - Soil analysis library
- **Loguru** - Advanced logging
- **PyYAML** - Configuration management

### Machine Learning
- **XGBoost** - Gradient boosting model for pump predictions
- **Flask** - ML model API server
- **NumPy** - Numerical computing
- **Scikit-learn** - ML utilities

### Web & API
- **Streamlit** - Interactive dashboard framework
- **Plotly** - Advanced data visualization
- **FastAPI** - Modern API framework for scheduler
- **Uvicorn** - ASGI server

### Data Storage
- **PostgreSQL 15** - Relational database
- **Alembic** - Database migrations

### Infrastructure
- **Docker & Docker Compose** - Container orchestration
- **Eclipse Mosquitto** - MQTT broker
- **Nginx** (optional) - Reverse proxy

### External APIs
- **Open-Meteo** - Weather forecasting API
- **OpenRouter** - LLM API for intelligent scheduling

---

## ✅ Prerequisites

### Software Requirements
- **Docker Desktop** (v20.10+) or Docker Engine + Docker Compose
- **4GB RAM minimum** (8GB recommended)
- **5GB free disk space**

### Network Requirements
The following ports must be available:
- `1883` - MQTT broker
- `5432` - PostgreSQL (mapped to 5433 externally)
- `8501` - Streamlit dashboard
- `8000` - ML service API
- `5002` - Scheduler API
- `9001` - MQTT WebSocket (optional)

### Optional
- IoT sensors with MQTT capability (ESP32, Raspberry Pi, etc.)
- MQTT client for testing (e.g., MQTT Explorer, mosquitto_sub)

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/defk0n1/WIEMPOWER2.git
cd WIEMPOWER2
```

### 2. Create Mosquitto Configuration

```bash
mkdir -p mosquitto/config mosquitto/data mosquitto/log
cat > mosquitto/config/mosquitto.conf << 'EOF'
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
EOF
```

### 3. Configure Environment Variables (Optional)

Create a `.env` file in the project root:

```bash
# Database
POSTGRES_USER=irrigation_user
POSTGRES_PASSWORD=irrigation_pass
POSTGRES_DB=irrigation_db

# MQTT
MQTT_BROKER=mosquitto
MQTT_PORT=1883

# Irrigation Job
IRRIGATION_JOB_INTERVAL_MINUTES=30

# ML Model
USE_MOCK_ML_MODEL=true
ML_MODEL_URL=http://ml-service:8000/predict

# Scheduler API
OPENROUTER_API_KEY=your-api-key-here
```

### 4. Build and Start Services

```bash
# Build all Docker images
docker-compose build

# Start all services in detached mode
docker-compose up -d

# View logs (all services)
docker-compose logs -f

# View specific service logs
docker-compose logs -f app
```

### 5. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8501
```

### 6. Verify System Status

```bash
# Check running containers
docker-compose ps

# Test MQTT broker
docker exec -it irrigation-mqtt-broker mosquitto_sub -t '#' -v

# Check database connection
docker exec -it irrigation-db psql -U irrigation_user -d irrigation_db -c "\dt"
```

---

## 📁 Project Structure

```
WIEMPOWER2/
├── config/                      # Configuration files
│   ├── mqtt_config.yaml        # MQTT topics and zones
│   ├── soil_config.yaml        # Soil properties and thresholds
│   └── npk_config.yaml         # NPK thresholds and crop requirements
│
├── src/                         # Core application modules
│   ├── mqtt_client.py          # MQTT subscriber and publisher
│   ├── data_storage.py         # Database models and operations
│   ├── soil_analyzer.py        # PAW calculation and moisture analysis
│   ├── npk_analyzer.py         # NPK level analysis
│   ├── irrigation_predictor.py # Irrigation decision logic
│   ├── irrigation_job.py       # Scheduled automation
│   ├── pump_model_client.py    # ML model API client
│   └── water_pump_simulator.py # Virtual pump for testing
│
├── streamlit-app/               # Web dashboard
│   └── dashboard.py            # Streamlit dashboard application
│
├── ml/                          # Machine learning service
│   ├── pump_model.py           # XGBoost model API (Flask)
│   ├── xgb_pump_model.pkl      # Trained model file
│   ├── Dockerfile              # ML service container
│   └── requirements.txt        # Python dependencies
│
├── scheduler/                   # Scheduling service
│   ├── main.py                 # FastAPI scheduler with LLM
│   ├── Dockerfile              # Scheduler container
│   └── requirements.txt        # Python dependencies
│
├── data/                        # Data and generators
│   └── mock_data_generator.py  # IoT sensor simulator
│
├── scripts/                     # Utility scripts
│   ├── init_db.sql             # Database initialization
│   └── entrypoint.sh           # Container entrypoint
│
├── mosquitto/                   # MQTT broker data
│   ├── config/                 # Mosquitto configuration
│   ├── data/                   # Persistent data
│   └── log/                    # MQTT logs
│
├── main.py                      # Main application entry point
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Main app container
├── requirements.txt             # Python dependencies
└── readme.md                    # This file
```

---

## ⚙️ Configuration

### 1. MQTT Configuration (`config/mqtt_config.yaml`)

```yaml
mqtt:
  broker: mosquitto              # MQTT broker hostname
  port: 1883                     # MQTT port
  client_id: irrigation_collector

topics:
  # Sensor topics
  soil_moisture: sensors/soil/moisture
  soil_temperature: sensors/soil/temperature
  air_temperature: sensors/air/temperature
  air_humidity: sensors/air/humidity
  rainfall: sensors/weather/rainfall
  soil_nitrogen: sensors/soil/npk/nitrogen
  soil_phosphorus: sensors/soil/npk/phosphorus
  soil_potassium: sensors/soil/npk/potassium
  water_level: sensors/water/level
  
  # Actuator topics
  irrigation_command: actuators/irrigation/command

sensor_zones:
  - zone_id: zone_1
    name: North Field
    depth_cm: 30
    crop_type: wheat
  - zone_id: zone_2
    name: South Field
    depth_cm: 30
    crop_type: corn

water_reservoir:
  capacity_liters: 10000
  min_level_percent: 20
  refill_rate_liters_per_hour: 500
```

### 2. Soil Configuration (`config/soil_config.yaml`)

```yaml
soil_properties:
  zone_1:
    name: "North Field"
    clay: 28.0                   # Percentage
    silt: 42.0
    sand: 30.0
    organic_matter: 2.5
    bulk_density: 1.35           # g/cm³
    soil_type: "HeS"             # Heavy Sand
    depth_layers: [0, 30, 60, 90] # cm

irrigation:
  threshold_paw_percentage: 50   # Irrigate when PAW < 50%
  application_rate_mm: 25        # Application depth
  min_interval_hours: 24         # Minimum time between irrigations
  max_daily_mm: 50               # Maximum daily application

alerts:
  critical_moisture_pct: 20
  warning_moisture_pct: 30
  email_enabled: false
```

### 3. NPK Configuration (`config/npk_config.yaml`)

```yaml
npk_thresholds:
  nitrogen:
    critical_low: 20             # mg/kg
    low: 40
    optimal_min: 60
    optimal_max: 120
    high: 150

crop_requirements:
  wheat:
    N: {min: 80, max: 120}
    P: {min: 30, max: 50}
    K: {min: 150, max: 250}
  corn:
    N: {min: 100, max: 150}
    P: {min: 40, max: 60}
    K: {min: 180, max: 280}

fertilizer_application:
  N_deficit_rate_kg_per_ha: 50   # kg/ha per 20 mg/kg deficit
  P_deficit_rate_kg_per_ha: 30
  K_deficit_rate_kg_per_ha: 40
  min_interval_days: 14          # Minimum between applications
```

---

## 🐳 Services

### Service Overview

| Service | Container Name | Port | Description |
|---------|---------------|------|-------------|
| **mosquitto** | irrigation-mqtt-broker | 1883, 9001 | MQTT message broker |
| **postgres** | irrigation-db | 5433:5432 | PostgreSQL database |
| **app** | irrigation-app | - | Main monitoring application |
| **dashboard** | irrigation-dashboard | 8501 | Streamlit web UI |
| **ml-service** | ml-model-service | 8000 | XGBoost ML API |
| **scheduler-api-service** | irrigation-api | 5002 | Weather & scheduling API |

### Service Details

#### 1. Main Application (`app`)

**Purpose**: Core MQTT consumer and irrigation controller

**Key Functions**:
- Subscribes to all sensor MQTT topics
- Processes sensor data in real-time
- Analyzes soil moisture and NPK levels
- Makes irrigation and fertilization decisions
- Stores all data to PostgreSQL
- Publishes actuator commands

**Environment Variables**:
- `MQTT_BROKER` - MQTT broker hostname
- `DATABASE_URL` - PostgreSQL connection string
- `IRRIGATION_JOB_INTERVAL_MINUTES` - Job frequency
- `USE_MOCK_ML_MODEL` - Use mock ML model (true/false)

#### 2. Streamlit Dashboard (`dashboard`)

**Purpose**: Web-based monitoring and visualization

**Features**:
- Real-time sensor data display
- Historical trend charts
- NPK status monitoring
- Irrigation event timeline
- Water level tracking
- Auto-refresh capability

**Access**: `http://localhost:8501`

#### 3. ML Service (`ml-service`)

**Purpose**: Machine learning predictions for pump control

**API Endpoint**: `POST http://localhost:8000/predict`

**Request Body**:
```json
{
  "Temperature": 25.5,
  "Humidity": 65.0,
  "water_level": 45.2
}
```

**Response**:
```json
{
  "prediction": 1,
  "confidence": 0.87,
  "model_version": "v1.0.0-xgboost"
}
```

#### 4. Scheduler API (`scheduler-api-service`)

**Purpose**: Weather forecasting and LLM-based scheduling

**API Endpoints**:
- `GET /health` - Health check
- `POST /generate-schedule` - Generate irrigation schedule

**Access**: `http://localhost:5002/docs` (Swagger UI)

#### 5. PostgreSQL (`postgres`)

**Purpose**: Persistent data storage

**Database**: `irrigation_db`

**Tables**:
- `sensor_readings` - All sensor data
- `npk_readings` - NPK nutrient levels
- `humidity_readings` - Humidity data
- `water_levels` - Reservoir levels
- `irrigation_events` - Irrigation history
- `fertilizer_events` - Fertilization history

**Access**:
```bash
docker exec -it irrigation-db psql -U irrigation_user -d irrigation_db
```

---

## 📡 IoT Sensor Integration

### MQTT Message Format

All sensor data must be published as JSON to the appropriate MQTT topic.

#### Soil Moisture

**Topic**: `sensors/soil/moisture`

```json
{
  "timestamp": "2025-11-02T08:30:00Z",
  "zone_id": "zone_1",
  "depth_cm": 30,
  "value": 28.5,
  "unit": "percent",
  "sensor_id": "moisture_01"
}
```

#### NPK Sensors

**Topics**: 
- `sensors/soil/npk/nitrogen`
- `sensors/soil/npk/phosphorus`
- `sensors/soil/npk/potassium`

```json
{
  "timestamp": "2025-11-02T08:30:00Z",
  "zone_id": "zone_1",
  "depth_cm": 30,
  "value": 95.3,
  "unit": "mg/kg",
  "sensor_id": "npk_01"
}
```

#### Water Level

**Topic**: `sensors/water/level`

```json
{
  "timestamp": "2025-11-02T08:30:00Z",
  "level_percent": 75.5,
  "current_liters": 7550,
  "capacity_liters": 10000,
  "water_height_cm": 150,
  "tank_status": "normal",
  "sensor_id": "water_level_01"
}
```

#### Temperature

**Topics**: 
- `sensors/soil/temperature`
- `sensors/air/temperature`

```json
{
  "timestamp": "2025-11-02T08:30:00Z",
  "zone_id": "zone_1",
  "value": 22.5,
  "unit": "celsius",
  "depth_cm": 30,
  "sensor_id": "temp_01",
  "sensor_type": "DS18B20"
}
```

#### Humidity

**Topic**: `sensors/air/humidity`

```json
{
  "timestamp": "2025-11-02T08:30:00Z",
  "zone_id": "zone_1",
  "humidity": 68.5,
  "temperature": 24.3,
  "heat_index": 25.1,
  "dew_point": 18.2,
  "sensor_id": "dht22_01",
  "sensor_type": "DHT22"
}
```

### ESP32 Example Code

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "YOUR_SERVER_IP";
const int mqtt_port = 1883;

WiFiClient espClient;
PubSubClient client(espClient);

void publishSoilMoisture(float moisture, String zone_id) {
  StaticJsonDocument<256> doc;
  doc["timestamp"] = getISOTimestamp();  // Implement this function
  doc["zone_id"] = zone_id;
  doc["depth_cm"] = 30;
  doc["value"] = moisture;
  doc["unit"] = "percent";
  doc["sensor_id"] = "esp32_moisture_01";
  
  char buffer[256];
  serializeJson(doc, buffer);
  client.publish("sensors/soil/moisture", buffer);
}

void publishNPK(float nitrogen, float phosphorus, float potassium, String zone_id) {
  StaticJsonDocument<256> doc;
  String timestamp = getISOTimestamp();
  
  // Nitrogen
  doc["timestamp"] = timestamp;
  doc["zone_id"] = zone_id;
  doc["depth_cm"] = 30;
  doc["value"] = nitrogen;
  doc["unit"] = "mg/kg";
  doc["sensor_id"] = "esp32_npk_01";
  
  char buffer[256];
  serializeJson(doc, buffer);
  client.publish("sensors/soil/npk/nitrogen", buffer);
  
  // Repeat for phosphorus and potassium...
}

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  
  // Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // Read sensors and publish
  float moisture = readMoistureSensor();
  publishSoilMoisture(moisture, "zone_1");
  
  delay(60000);  // Publish every minute
}
```

### Raspberry Pi Example (Python)

```python
import paho.mqtt.client as mqtt
import json
from datetime import datetime, timezone

MQTT_BROKER = "your-server-ip"
MQTT_PORT = 1883

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

def publish_moisture(value, zone_id="zone_1"):
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zone_id": zone_id,
        "depth_cm": 30,
        "value": value,
        "unit": "percent",
        "sensor_id": "rpi_moisture_01"
    }
    client.publish("sensors/soil/moisture", json.dumps(payload))

# Main loop
while True:
    moisture = read_sensor()  # Implement sensor reading
    publish_moisture(moisture)
    time.sleep(60)
```

---

## 📚 API Documentation

### ML Service API

**Base URL**: `http://localhost:8000`

#### Health Check

```bash
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "model": "xgboost",
  "version": "v1.0.0-xgboost"
}
```

#### Predict Pump Activation

```bash
POST /predict
Content-Type: application/json

{
  "Temperature": 25.5,
  "Humidity": 65.0,
  "water_level": 45.2
}
```

**Response**:
```json
{
  "prediction": 1,
  "probability": 0.87,
  "model_version": "v1.0.0-xgboost",
  "timestamp": "2025-11-02T08:30:00Z"
}
```

### Scheduler API

**Base URL**: `http://localhost:5002`

**Documentation**: `http://localhost:5002/docs` (Swagger UI)

#### Generate Schedule

```bash
POST /generate-schedule
```

**Response**:
```json
{
  "schedule": "Irrigation schedule for next 7 days...",
  "weather_forecast": [...],
  "recommendations": [...]
}
```

---

## 💻 Development

### Local Development Setup

1. **Clone repository**:
   ```bash
   git clone https://github.com/defk0n1/WIEMPOWER2.git
   cd WIEMPOWER2
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run services individually**:
   ```bash
   # Start database and MQTT only
   docker-compose up -d postgres mosquitto
   
   # Run main app locally
   python main.py
   
   # Run dashboard locally
   streamlit run streamlit-app/dashboard.py
   ```

### Running Tests

```bash
# Run mock data generator for testing
docker-compose run app python data/mock_data_generator.py

# Test MQTT publishing
mosquitto_pub -h localhost -t "sensors/soil/moisture" -m '{"timestamp":"2025-11-02T08:00:00Z","zone_id":"zone_1","value":25.5,"unit":"percent"}'
```

### Adding New Sensors

1. **Update MQTT config** (`config/mqtt_config.yaml`):
   ```yaml
   topics:
     new_sensor: sensors/custom/newsensor
   ```

2. **Add handler in main.py**:
   ```python
   elif 'newsensor' in topic:
       self._handle_new_sensor(payload, timestamp)
   ```

3. **Update database schema** if needed in `src/data_storage.py`

---

## 🛠️ Useful Commands

### Docker Operations

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f app

# Restart services
docker-compose restart

# Restart specific service
docker-compose restart app

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Rebuild specific service
docker-compose build app
docker-compose up -d app

# View container resource usage
docker stats
```

### Database Operations

```bash
# Access PostgreSQL
docker exec -it irrigation-db psql -U irrigation_user -d irrigation_db

# Common queries
\dt                              # List tables
SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM npk_readings ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM irrigation_events ORDER BY timestamp DESC;

# Export data
docker exec irrigation-db pg_dump -U irrigation_user irrigation_db > backup.sql

# Import data
docker exec -i irrigation-db psql -U irrigation_user irrigation_db < backup.sql
```

### MQTT Operations

```bash
# Subscribe to all topics
docker exec -it irrigation-mqtt-broker mosquitto_sub -t '#' -v

# Subscribe to specific topic
docker exec -it irrigation-mqtt-broker mosquitto_sub -t 'sensors/soil/moisture' -v

# Publish test message
docker exec -it irrigation-mqtt-broker mosquitto_pub -t 'sensors/soil/moisture' -m '{"timestamp":"2025-11-02T08:00:00Z","zone_id":"zone_1","value":25.5,"unit":"percent"}'

# Check MQTT broker status
docker exec -it irrigation-mqtt-broker mosquitto_sub -t '$SYS/#' -v
```

### Application Logs

```bash
# View application logs
docker-compose logs -f app

# View last 100 lines
docker-compose logs --tail=100 app

# Save logs to file
docker-compose logs app > app_logs.txt

# View logs inside container
docker exec irrigation-app tail -f logs/irrigation_app_*.log
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use

**Error**: `Bind for 0.0.0.0:8501 failed: port is already allocated`

**Solution**: Change ports in `docker-compose.yml`:
```yaml
dashboard:
  ports:
    - "8502:8501"  # Change external port
```

#### 2. Database Connection Failed

**Symptoms**: App can't connect to PostgreSQL

**Solution**:
```bash
# Check if database is ready
docker-compose logs postgres

# Wait for database healthcheck
docker-compose ps

# Restart app service
docker-compose restart app
```

#### 3. MQTT Broker Not Responding

**Symptoms**: Sensors can't publish data

**Solution**:
```bash
# Check mosquitto logs
docker-compose logs mosquitto

# Verify configuration
cat mosquitto/config/mosquitto.conf

# Restart broker
docker-compose restart mosquitto

# Test connection
mosquitto_pub -h localhost -p 1883 -t 'test' -m 'hello'
```

#### 4. Dashboard Not Loading

**Symptoms**: Dashboard shows connection error

**Solution**:
```bash
# Check dashboard logs
docker-compose logs dashboard

# Verify database connection
docker exec -it irrigation-db psql -U irrigation_user -d irrigation_db -c "SELECT 1"

# Restart dashboard
docker-compose restart dashboard
```

#### 5. ML Service Errors

**Symptoms**: Pump predictions fail

**Solution**:
```bash
# Check ML service logs
docker-compose logs ml-service

# Test ML endpoint
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"Temperature":25,"Humidity":60,"water_level":45}'

# Use mock model instead
# In docker-compose.yml, set: USE_MOCK_ML_MODEL=true
```

#### 6. Permission Denied Errors

**Symptoms**: Container can't write to volumes

**Solution**:
```bash
# Fix mosquitto permissions
sudo chown -R 1883:1883 mosquitto/data mosquitto/log

# Fix logs directory
sudo chmod -R 777 logs/
```

### Debug Mode

Enable debug logging by modifying `main.py`:

```python
logger.add(sys.stdout, level="DEBUG")  # Change from INFO to DEBUG
```

### Health Checks

```bash
# Check all services health
docker-compose ps

# Test MQTT
mosquitto_sub -h localhost -t '$SYS/broker/uptime' -C 1

# Test Database
docker exec irrigation-db pg_isready -U irrigation_user

# Test ML Service
curl http://localhost:8000/health

# Test Scheduler
curl http://localhost:5002/health
```

---

## 📄 License

MIT License - Feel free to use and modify

Copyright (c) 2025 defk0n1

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Roadmap

**Planned Features:**
- [ ] Weather API integration (Open-Meteo)
- [ ] Email/SMS alert notifications
- [ ] Mobile app (React Native)
- [ ] Multi-crop optimization
- [ ] Advanced ML models (LSTM for time-series)
- [ ] Satellite imagery integration
- [ ] Automated pH monitoring
- [ ] Integration with irrigation hardware
- [ ] GraphQL API
- [ ] Kubernetes deployment manifests

**Completed:**
- [x] NPK monitoring and fertilization
- [x] Water level tracking
- [x] ML-powered pump control
- [x] Streamlit dashboard
- [x] Scheduled irrigation jobs
- [x] Multi-zone support
- [x] Docker containerization

---

## 📞 Support

For issues and questions:
- **GitHub Issues**: [Create an issue](https://github.com/defk0n1/WIEMPOWER2/issues)
- **Documentation**: This README
- **Logs**: Check `docker-compose logs`

---

**Happy Farming! 🌾🚜**

*Built with ❤️ for precision agriculture*