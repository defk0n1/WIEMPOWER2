# Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): 2025-11-02 03:06:03
# Current User's Login: defk0n1

import os
import sys
import time
import yaml
import json
from datetime import datetime, timezone
from loguru import logger
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from irrigation_job import IrrigationJob
from mqtt_client import SensorDataCollector as MQTTClient
from data_storage import DatabaseManager
from soil_analyzer import SoilAnalyzer
from irrigation_predictor import IrrigationController
from npk_analyzer import NPKAnalyzer

# Load environment variables
load_dotenv()

# Configure logger
logger.remove()
logger.add(sys.stdout, 
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
           level="INFO")

os.makedirs('logs', exist_ok=True)
logger.add("logs/irrigation_app_{time}.log", rotation="1 day", retention="7 days")


class IrrigationMonitoringSystem:
    def __init__(self):
        # Load configurations
        self.load_configs()
            # Initialize irrigation job
        job_interval = int(os.getenv('IRRIGATION_JOB_INTERVAL_MINUTES', '30'))
        ml_model_url = os.getenv('ML_MODEL_URL', None)
        use_mock_model = os.getenv('USE_MOCK_ML_MODEL', 'true').lower() == 'true'
        
        
        # Initialize database
        db_url = os.getenv('DATABASE_URL', 
            'postgresql://irrigation_user:irrigation_pass@postgres:5432/irrigation_db')
        self.db_manager = DatabaseManager(db_url)
        
        # Initialize analyzers
        self.soil_analyzer = SoilAnalyzer(self.soil_config, self.db_manager)
        self.npk_analyzer = NPKAnalyzer('config/npk_config.yaml', self.db_manager)
        
        # Initialize MQTT client
        self.mqtt_client = MQTTClient(
            config_path='config/mqtt_config.yaml',
            db_manager=self.db_manager
        )
        
        # Initialize irrigation controller
        self.irrigation_controller = IrrigationController(
            mqtt_broker=self.mqtt_config['mqtt']['broker'],
            mqtt_port=self.mqtt_config['mqtt']['port'],
            db_manager=self.db_manager,
            soil_analyzer=self.soil_analyzer,
            mqtt_client=None
        )


        self.irrigation_job = IrrigationJob(
            db_manager=self.db_manager,
            mqtt_client=None,
            ml_model_url=ml_model_url,
            interval_minutes=job_interval,
            use_mock_model=use_mock_model
    )
        
        # NPK tracking per zone
        self.zone_npk_state = {}
        
        # Sensor data counters for statistics
        self.sensor_stats = {
            'npk_nitrogen': 0,
            'npk_phosphorus': 0,
            'npk_potassium': 0,
            'water_level': 0,
            'moisture': 0,
            'temperature': 0,
            'humidity': 0,
            'rainfall': 0,
            'other': 0
        }
        
        # Override on_message
        self.mqtt_client.on_message = self._custom_on_message
        
    def load_configs(self):
        """Load YAML configuration files"""
        try:
            logger.info("📄 Loading configurations...")
            
            with open('config/mqtt_config.yaml', 'r') as f:
                self.mqtt_config = yaml.safe_load(f)
            
            with open('config/soil_config.yaml', 'r') as f:
                self.soil_config = yaml.safe_load(f)
                
            logger.info("✅ Configurations loaded successfully")
            
        except FileNotFoundError as e:
            logger.error(f"❌ Config file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
            raise
    
    def _custom_on_message(self, client, userdata, msg):
        """Custom message handler for ALL sensor types - displays everything"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Parse timestamp
            timestamp_str = payload.get('timestamp')
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.now(timezone.utc)
            
            # Extract common fields
            zone_id = payload.get('zone_id', 'N/A')
            sensor_id = payload.get('sensor_id', 'unknown')
            value = payload.get('value')
            unit = payload.get('unit', '')
            
            # ==================== NPK SENSORS ====================
            if 'npk/nitrogen' in topic:
                self.sensor_stats['npk_nitrogen'] += 1
                logger.info(f"🌿 [NPK-N] Zone: {zone_id} | Nitrogen: {value} {unit} | Depth: {payload.get('depth_cm', 'N/A')}cm | Sensor: {sensor_id}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                self._handle_npk_reading(zone_id, 'nitrogen', value, timestamp, payload)
                
            elif 'npk/phosphorus' in topic:
                self.sensor_stats['npk_phosphorus'] += 1
                logger.info(f"🌿 [NPK-P] Zone: {zone_id} | Phosphorus: {value} {unit} | Depth: {payload.get('depth_cm', 'N/A')}cm | Sensor: {sensor_id}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                self._handle_npk_reading(zone_id, 'phosphorus', value, timestamp, payload)
                
            elif 'npk/potassium' in topic:
                self.sensor_stats['npk_potassium'] += 1
                logger.info(f"🌿 [NPK-K] Zone: {zone_id} | Potassium: {value} {unit} | Depth: {payload.get('depth_cm', 'N/A')}cm | Sensor: {sensor_id}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                self._handle_npk_reading(zone_id, 'potassium', value, timestamp, payload)
            
            # ==================== WATER LEVEL SENSOR ====================
            elif 'water/level' in topic:
                self.sensor_stats['water_level'] += 1
                level_percent = payload.get('level_percent', 0)
                current_liters = payload.get('current_liters', 0)
                capacity_liters = payload.get('capacity_liters', 0)
                water_height = payload.get('water_height_cm', 'N/A')
                tank_status = payload.get('tank_status', 'unknown')
                
                logger.info(f"💧 [WATER] Level: {level_percent}% | Current: {current_liters}L | Capacity: {capacity_liters}L | Height: {water_height}cm | Status: {tank_status}")
                logger.debug(f"   └─ Sensor: {sensor_id} | Type: {payload.get('sensor_type', 'N/A')}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                self._handle_water_level(payload, timestamp)
            
            # ==================== SOIL MOISTURE SENSOR ====================
            elif 'moisture' in topic:
                self.sensor_stats['moisture'] += 1
                depth_cm = payload.get('depth_cm', 'N/A')
                logger.info(f"💦 [MOISTURE] Zone: {zone_id} | Moisture: {value}{unit} | Depth: {depth_cm}cm | Sensor: {sensor_id}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                
                self.db_manager.store_sensor_reading(
                    timestamp=timestamp,
                    zone_id=zone_id,
                    sensor_type='moisture',
                    value=value,
                    unit=unit,
                    depth_cm=payload.get('depth_cm')
                )
                self.analyze_and_act(payload, timestamp)
            
            # ==================== TEMPERATURE SENSORS ====================
            elif 'temperature' in topic:
                self.sensor_stats['temperature'] += 1
                sensor_type = payload.get('sensor_type', 'Unknown')
                rom_code = payload.get('rom_code', 'N/A')
                depth_cm = payload.get('depth_cm', 'N/A')
                
                if 'soil' in topic:
                    logger.info(f"🌡️  [SOIL-TEMP] Zone: {zone_id} | Temperature: {value}{unit} | Depth: {depth_cm}cm")
                elif 'air' in topic:
                    logger.info(f"🌡️  [AIR-TEMP] Zone: {zone_id} | Temperature: {value}{unit}")
                else:
                    logger.info(f"🌡️  [TEMP] Zone: {zone_id} | Temperature: {value}{unit} | Depth: {depth_cm}cm")
                
                logger.debug(f"   └─ Sensor: {sensor_id} | Type: {sensor_type} | ROM: {rom_code}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                
                self.db_manager.store_sensor_reading(
                    timestamp=timestamp,
                    zone_id=zone_id,
                    sensor_type='temperature',
                    value=value,
                    unit=unit,
                    depth_cm=payload.get('depth_cm')
                )
            
            # ==================== HUMIDITY SENSOR ====================
            elif 'humidity' in topic:
                self.sensor_stats['humidity'] += 1
                humidity = payload.get('humidity')
                temperature = payload.get('temperature')
                heat_index = payload.get('heat_index')
                dew_point = payload.get('dew_point')
                sensor_type = payload.get('sensor_type', 'Unknown')
                
                logger.info(f"🌫️  [HUMIDITY] Zone: {zone_id} | Humidity: {humidity}% RH | Air Temp: {temperature}°C")
                logger.info(f"   └─ Heat Index: {heat_index}°C | Dew Point: {dew_point}°C | Sensor Type: {sensor_type}")
                logger.debug(f"   └─ Sensor ID: {sensor_id}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                
                self._handle_humidity(payload, timestamp)
            
            # ==================== RAINFALL SENSOR ====================
            elif 'rainfall' in topic:
                self.sensor_stats['rainfall'] += 1
                logger.info(f"🌧️  [RAINFALL] Zone: {zone_id} | Rainfall: {value}{unit} | Sensor: {sensor_id}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                
                self.db_manager.store_sensor_reading(
                    timestamp=timestamp,
                    zone_id=zone_id,
                    sensor_type='rainfall',
                    value=value,
                    unit=unit,
                    depth_cm=None
                )
            
            # ==================== UNKNOWN/OTHER SENSORS ====================
            else:
                self.sensor_stats['other'] += 1
                sensor_type = topic.split('/')[-1]
                logger.info(f"📡 [UNKNOWN] Topic: {topic} | Zone: {zone_id} | Value: {value}{unit}")
                logger.info(f"   └─ Sensor Type: {sensor_type} | Sensor ID: {sensor_id}")
                logger.debug(f"   └─ Full payload: {json.dumps(payload, indent=2)}")
                
                # Try to store generically
                try:
                    self.db_manager.store_sensor_reading(
                        timestamp=timestamp,
                        zone_id=zone_id if zone_id != 'N/A' else 'unknown',
                        sensor_type=sensor_type,
                        value=value if value is not None else 0,
                        unit=unit,
                        depth_cm=payload.get('depth_cm')
                    )
                except Exception as e:
                    logger.warning(f"   └─ Could not store unknown sensor data: {e}")
            
            # Display statistics every 50 messages
            total_messages = sum(self.sensor_stats.values())
            if total_messages % 50 == 0:
                self._display_statistics()
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in message from {msg.topic}: {e}")
            logger.debug(f"   └─ Raw payload: {msg.payload}")
        except Exception as e:
            logger.error(f"❌ Error in custom handler for topic {msg.topic}: {e}")
            import traceback
            traceback.print_exc()
            logger.debug(f"   └─ Payload: {msg.payload}")
    
    def _display_statistics(self):
        """Display sensor data reception statistics"""
        total = sum(self.sensor_stats.values())
        logger.info("=" * 60)
        logger.info(f"📊 SENSOR DATA STATISTICS (Total: {total} messages)")
        logger.info("=" * 60)
        logger.info(f"   🌿 NPK Nitrogen:    {self.sensor_stats['npk_nitrogen']:>5} messages")
        logger.info(f"   🌿 NPK Phosphorus:  {self.sensor_stats['npk_phosphorus']:>5} messages")
        logger.info(f"   🌿 NPK Potassium:   {self.sensor_stats['npk_potassium']:>5} messages")
        logger.info(f"   💧 Water Level:     {self.sensor_stats['water_level']:>5} messages")
        logger.info(f"   💦 Soil Moisture:   {self.sensor_stats['moisture']:>5} messages")
        logger.info(f"   🌡️  Temperature:     {self.sensor_stats['temperature']:>5} messages")
        logger.info(f"   🌫️  Humidity:        {self.sensor_stats['humidity']:>5} messages")
        logger.info(f"   🌧️  Rainfall:        {self.sensor_stats['rainfall']:>5} messages")
        logger.info(f"   📡 Other:           {self.sensor_stats['other']:>5} messages")
        logger.info("=" * 60)
    
    def _handle_npk_reading(self, zone_id, nutrient_type, value, timestamp, payload):
        """Handle NPK sensor readings"""
        # Initialize zone NPK state if needed
        if zone_id not in self.zone_npk_state:
            self.zone_npk_state[zone_id] = {
                'nitrogen': None,
                'phosphorus': None,
                'potassium': None,
                'crop_type': 'wheat'
            }
        
        # Update the specific nutrient
        self.zone_npk_state[zone_id][nutrient_type] = value
        
        # Check if we have all three NPK values
        state = self.zone_npk_state[zone_id]
        if all(state[n] is not None for n in ['nitrogen', 'phosphorus', 'potassium']):
            logger.info(f"   └─ ✅ Complete NPK data for {zone_id}: N={state['nitrogen']}, P={state['phosphorus']}, K={state['potassium']}")
            
            # Store NPK reading in database
            try:
                self.db_manager.store_npk_reading(
                    timestamp=timestamp,
                    zone_id=zone_id,
                    nitrogen=state['nitrogen'],
                    phosphorus=state['phosphorus'],
                    potassium=state['potassium'],
                    depth_cm=payload.get('depth_cm')
                )
                logger.debug(f"   └─ ✅ Stored NPK reading in database")
            except Exception as e:
                logger.error(f"   └─ ❌ Failed to store NPK reading: {e}")
            
            # Analyze NPK levels
            self._analyze_npk(zone_id, timestamp)
    
    def _analyze_npk(self, zone_id, timestamp):
        """Analyze NPK levels and recommend fertilization"""
        state = self.zone_npk_state[zone_id]
        
        analysis = self.npk_analyzer.analyze_npk(
            zone_id=zone_id,
            nitrogen=state['nitrogen'],
            phosphorus=state['phosphorus'],
            potassium=state['potassium'],
            crop_type=state.get('crop_type', 'wheat')
        )
        
        # Status emojis
        n_emoji = {"CRITICAL": "🔴", "LOW": "🟡", "DEFICIENT": "🟡", "OPTIMAL": "🟢", "EXCESS": "⚪"}.get(analysis['nitrogen']['status'], "⚪")
        p_emoji = {"CRITICAL": "🔴", "LOW": "🟡", "DEFICIENT": "🟡", "OPTIMAL": "🟢", "EXCESS": "⚪"}.get(analysis['phosphorus']['status'], "⚪")
        k_emoji = {"CRITICAL": "🔴", "LOW": "🟡", "DEFICIENT": "🟡", "OPTIMAL": "🟢", "EXCESS": "⚪"}.get(analysis['potassium']['status'], "⚪")
        
        logger.info(f"🌿 {zone_id} NPK Status: "
                   f"{n_emoji}N={analysis['nitrogen']['status']} "
                   f"{p_emoji}P={analysis['phosphorus']['status']} "
                   f"{k_emoji}K={analysis['potassium']['status']}")
        
        # Log fertilization recommendations
        if analysis['fertilization_needed']:
            for rec in analysis['recommendations']:
                logger.warning(f"🌿 FERTILIZER NEEDED: {zone_id} - {rec['nutrient']}: {rec['amount_kg_per_ha']} kg/ha - {rec['reason']}")
                
                # Publish fertilizer command (automated)
                command = {
                    'zone_id': zone_id,
                    'nutrient': rec['nutrient'],
                    'amount_kg': rec['amount_kg_per_ha'],
                    'timestamp': timestamp.isoformat(),
                    'automated': True
                }
                self.mqtt_client.client.publish('actuators/fertilizer/command', json.dumps(command))
                
                # Log to database
                try:
                    self.db_manager.store_fertilizer_event(
                        timestamp=timestamp,
                        zone_id=zone_id,
                        nutrient=rec['nutrient'],
                        amount_kg=rec['amount_kg_per_ha'],
                        automated=True,
                        reason=rec['reason']
                    )
                except Exception as e:
                    logger.error(f"   └─ ❌ Failed to store fertilizer event: {e}")
    
    def _handle_water_level(self, payload, timestamp):
        """Handle water reservoir level readings"""
        current_liters = payload.get('current_liters')
        capacity_liters = payload.get('capacity_liters')
        level_percent = payload.get('level_percent')
        
        # Store in database
        try:
            self.db_manager.store_water_level(
                timestamp=timestamp,
                current_liters=current_liters,
                capacity_liters=capacity_liters,
                level_percent=level_percent
            )
            logger.debug(f"   └─ ✅ Stored water level in database")
        except Exception as e:
            logger.error(f"   └─ ❌ Failed to store water level: {e}")
        
        # Alert if low
        if level_percent < 20:
            logger.warning(f"   └─ ⚠️  WATER RESERVOIR LOW: {level_percent:.1f}% - Refill needed!")
        elif level_percent < 40:
            logger.info(f"   └─ ⚠️  Water level moderate: {level_percent:.1f}%")
    
    def analyze_and_act(self, moisture_data, timestamp):
        """Analyze moisture and use irrigation controller"""
        try:
            zone_id = moisture_data['zone_id']
            moisture_pct = moisture_data['value']
            
            # Perform soil analysis
            analysis = self.soil_analyzer.analyze_moisture(zone_id, moisture_pct)
            
            # Add metadata
            analysis['zone_id'] = zone_id
            analysis['timestamp'] = timestamp
            analysis['current_moisture_pct'] = moisture_pct
            
            # Status emoji
            status_emoji = {
                "CRITICAL": "🔴",
                "LOW": "🟡",
                "ADEQUATE": "🟢",
                "OPTIMAL": "💧"
            }.get(analysis['status'], "⚪")
            
            logger.info(f"   └─ {status_emoji} PAW={analysis['paw_percentage']:.1f}%, Status={analysis['status']}")
            
            # Use irrigation controller
            self.irrigation_controller.process_analysis(analysis)
                
        except Exception as e:
            logger.error(f"   └─ ❌ Error in moisture analysis: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_humidity(self, payload, timestamp):
        """Handle humidity sensor data"""
        zone_id = payload.get('zone_id')
        humidity = payload.get('humidity')
        temperature = payload.get('temperature')
        heat_index = payload.get('heat_index')
        dew_point = payload.get('dew_point')
        
        if humidity is None:
            logger.warning("   └─ ⚠️  Missing humidity value in payload")
            return
        
        # Determine humidity status
        if humidity < 30:
            status = "🔴 TOO DRY"
        elif humidity < 40:
            status = "🟡 LOW"
        elif humidity < 70:
            status = "🟢 OPTIMAL"
        elif humidity < 85:
            status = "🟡 HIGH"
        else:
            status = "🔴 TOO HUMID"
        
        logger.info(f"   └─ Status: {status}")
        
        # Store in database
        try:
            self.db_manager.store_humidity_reading(
                timestamp=timestamp,
                zone_id=zone_id,
                humidity=humidity,
                temperature=temperature,
                heat_index=heat_index,
                dew_point=dew_point
            )
            logger.debug(f"   └─ ✅ Stored humidity reading in database")
        except Exception as e:
            logger.error(f"   └─ ❌ Failed to store humidity reading: {e}")
        
        # Alert if conditions are problematic
        if humidity > 85:
            logger.warning(f"   └─ ⚠️  HIGH HUMIDITY ALERT - Risk of fungal diseases!")
        elif humidity < 30:
            logger.warning(f"   └─ ⚠️  LOW HUMIDITY ALERT - Consider misting")
    
    def run(self):
        """Start the monitoring system"""
        logger.info("=" * 60)
        logger.info("🌱 WIEMPOWER2 - IoT Irrigation Monitoring System")
        logger.info("=" * 60)
        
        # Initialize database tables
        logger.info("🔧 Initializing database...")
        try:
            self.db_manager.create_tables()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return
        
        # Connect to MQTT broker
        logger.info("🔌 Connecting to MQTT broker...")
        try:
            self.mqtt_client.connect()
            time.sleep(3)
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return
        
        # Verify connection
        if not self.mqtt_client.connected:
            logger.error("❌ MQTT connection not established")
            return
            # ✅ ADD THIS: Set MQTT client for irrigation job
        if hasattr(self, 'irrigation_job') and self.irrigation_job:
            logger.info("✅ Setting MQTT client for irrigation job...")
            self.irrigation_job.set_mqtt_client(self.mqtt_client.client)

        
        # Start irrigation job
        logger.info("🚀 Starting automated irrigation job...")
        self.irrigation_job.start()
        
        # Set MQTT client for irrigation controller
        self.irrigation_controller.mqtt_client = self.mqtt_client.client
        logger.info("✅ Irrigation controller connected to MQTT")
        
        logger.info("=" * 60)
        logger.info("✅ System running - Monitoring ALL sensors...")
        logger.info("📡 Subscribed Topics:")
        logger.info("   🌿 NPK Nutrients (N, P, K)")
        logger.info("   💧 Water Level")
        logger.info("   💦 Soil Moisture")
        logger.info("   🌡️  Temperature (Soil & Air)")
        logger.info("   🌫️  Humidity")
        logger.info("   🌧️  Rainfall")
        logger.info("=" * 60)
        logger.info("💡 Features:")
        logger.info("   ✅ Complete sensor data display")
        logger.info("   ✅ Automated irrigation decisions")
        logger.info("   ✅ Automated fertilization")
        logger.info("   ✅ Database storage")
        logger.info("   ✅ Real-time statistics")
        logger.info("=" * 60)
        logger.info("🚀 Starting automated irrigation job...")
        self.irrigation_job.start()
        
        logger.info("="*60)
        logger.info("✅ System running - Monitoring ALL sensors...")
        logger.info(f"⏰ Irrigation Job: Every {self.irrigation_job.interval_minutes} minutes")
        logger.info("="*60)
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n⏹️  Shutting down gracefully...")
            self._display_statistics()
            self.irrigation_job.stop()
            self.mqtt_client.stop()
            logger.info("👋 Goodbye!")


if __name__ == '__main__':
    try:
        system = IrrigationMonitoringSystem()
        system.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)