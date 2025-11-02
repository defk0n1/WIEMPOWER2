# 🌱 IoT Irrigation Monitoring & Prediction System

**MVP Docker-based solution for soil irrigation monitoring using farmingpy**

Built by: **defk0n1**  
Date: **2025-11-01**

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed
- 4GB RAM minimum
- Port 1883, 5432, 8501 available

### 1. Clone/Create Project

```bash
mkdir irrigation-mvp
cd irrigation-mvp
# Copy all files from this guide into the structure shown above
```

### 2. Create Mosquitto Config

```bash
mkdir -p mosquitto/config mosquitto/data mosquitto/log
cat > mosquitto/config/mosquitto.conf << EOF
listener 1883
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest file /mosquitto/log/mosquitto.log
log_dest stdout
EOF
```

### 3. Build and Run

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Access Dashboard

Open browser: **http://localhost:8501**

---

## 📊 Services

| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 8501 | Streamlit web interface |
| MQTT Broker | 1883 | Mosquitto message broker |
| PostgreSQL | 5432 | Time-series data storage |
| App | - | MQTT consumer & analyzer |
| Sensors | - | Mock IoT data generator |

---

## 🔌 Connect Real IoT Sensors

### MQTT Topics

```bash
# Soil Moisture
sensors/soil/moisture
{
  "timestamp": "2025-11-01T14:31:20Z",
  "zone_id": "zone_1",
  "depth_cm": 30,
  "value": 28.5,
  "unit": "percent"
}

# Soil Temperature
sensors/soil/temperature

# Air Temperature
sensors/air/temperature

# Air Humidity
sensors/air/humidity

# Rainfall
sensors/weather/rainfall
```

### Example: ESP32 Integration

```cpp
#include <WiFi.h>
#include <PubSubClient.h>

const char* mqtt_server = "YOUR_SERVER_IP";
const int mqtt_port = 1883;

void publishSoilMoisture(float value) {
  String payload = "{\"timestamp\":\"" + getISOTime() + 
                   "\",\"zone_id\":\"zone_1\"," +
                   "\"depth_cm\":30,\"value\":" + String(value) + 
                   ",\"unit\":\"percent\"}";
  
  client.publish("sensors/soil/moisture", payload.c_str());
}
```

---

## 🛠️ Useful Commands

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f app

# Restart services
docker-compose restart

# Stop everything
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Enter database
docker exec -it irrigation-db psql -U irrigation_user -d irrigation_db

# Check MQTT messages
docker exec -it irrigation-mqtt-broker mosquitto_sub -t '#' -v
```

---

## 📈 Features

✅ Real-time soil moisture monitoring  
✅ Automated irrigation recommendations  
✅ PAW (Plant Available Water) calculation  
✅ Historical data visualization  
✅ MQTT IoT sensor integration  
✅ Farmingpy soil analysis  
✅ PostgreSQL time-series storage  
✅ Web dashboard (Streamlit)  
✅ Docker containerized  

---

## 🔧 Configuration

Edit `config/soil_config.yaml` to customize:
- Irrigation thresholds
- Soil properties per zone
- Application rates

Edit `config/mqtt_config.yaml` for:
- MQTT broker settings
- Topic structure
- Zone definitions

---

## 📚 Architecture

```
IoT Sensors (Real/Mock)
    ↓
MQTT Broker (Mosquitto)
    ↓
Python App (MQTT Consumer)
    ↓
Soil Analyzer (farmingpy)
    ↓
PostgreSQL Database
    ↓
Streamlit Dashboard
```

---

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Change ports in docker-compose.yml
ports:
  - "8502:8501"  # Change 8501 to 8502
```

**Database connection issues:**
```bash
# Check database is ready
docker-compose logs postgres
```

**MQTT not connecting:**
```bash
# Verify broker is running
docker-compose logs mosquitto
```

---

## 📝 License

MIT License - Feel free to use and modify

---

## 🤝 Contributing

Built as MVP - extend as needed!

**Next Steps:**
- Add weather API integration
- Implement APSIM simulations
- Add email/SMS alerts
- Multi-crop support
- Mobile app

---

**Happy Farming! 🌾**