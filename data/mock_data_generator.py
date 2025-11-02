#!/usr/bin/env python3
import os
import sys
import json
import time
import random
import math
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from loguru import logger
import yaml

class MockSensorGenerator:
    def __init__(self):
        # Initialize ALL attributes FIRST
        self.broker = 'mosquitto'
        self.port = 1883
        self.zones = []
        self.zone_state = {}
        self.hour_of_day = 12
        self.evapotranspiration_rate = 0.15
        self.iteration_count = 0
        
        # NEW: Water reservoir state
        self.water_reservoir = {
            'capacity_liters': 10000,
            'current_level_liters': 8000,
            'min_level_percent': 20
        }
        
        # Load config
        self.load_config()
        
        # MQTT client setup
        self.client = mqtt.Client(client_id="sensor_simulator", clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
    def load_config(self):
        """Load configuration from YAML"""
        config_path = '/app/config/mqtt_config.yaml'
        
        try:
            logger.info(f"Loading config from {config_path}")
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.broker = config.get('mqtt', {}).get('broker', 'mosquitto')
            self.port = config.get('mqtt', {}).get('port', 1883)
            self.zones = config.get('sensor_zones', [])
            
            # Water reservoir config
            reservoir_config = config.get('water_reservoir', {})
            self.water_reservoir['capacity_liters'] = reservoir_config.get('capacity_liters', 10000)
            self.water_reservoir['current_level_liters'] = self.water_reservoir['capacity_liters'] * 0.8
            self.water_reservoir['min_level_percent'] = reservoir_config.get('min_level_percent', 20)
            
            # Initialize state for each zone
            for zone in self.zones:
                zone_id = zone['zone_id']
                crop_type = zone.get('crop_type', 'wheat')
                
                self.zone_state[zone_id] = {
                    'soil_moisture': random.uniform(20, 25),
                    'soil_temp': 15.0,
                    'air_temp': 18.0,
                    'air_humidity': 60.0,
                    'last_rainfall': 0,
                    'irrigation_active': False,
                    # NEW: NPK levels (start in optimal range)
                    'nitrogen': random.uniform(80, 120),      # mg/kg
                    'phosphorus': random.uniform(35, 55),     # mg/kg
                    'potassium': random.uniform(170, 270),    # mg/kg
                    'crop_type': crop_type
                }
            
            logger.info(f"✅ Configuration loaded: {len(self.zones)} zones")
            
        except FileNotFoundError:
            logger.warning(f"Config file not found, using defaults")
            self._use_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self._use_default_config()
    
    def _use_default_config(self):
        """Fallback to default configuration"""
        self.broker = 'mosquitto'
        self.port = 1883
        self.zones = [
            {'zone_id': 'zone_1', 'name': 'North Field', 'depth_cm': 30, 'crop_type': 'wheat'},
            {'zone_id': 'zone_2', 'name': 'South Field', 'depth_cm': 30, 'crop_type': 'corn'}
        ]
        
        for zone in self.zones:
            zone_id = zone['zone_id']
            self.zone_state[zone_id] = {
                'soil_moisture': random.uniform(20, 25),
                'soil_temp': 15.0,
                'air_temp': 18.0,
                'air_humidity': 60.0,
                'last_rainfall': 0,
                'irrigation_active': False,
                'nitrogen': random.uniform(80, 120),
                'phosphorus': random.uniform(35, 55),
                'potassium': random.uniform(170, 270),
                'crop_type': 'wheat'
            }
        
        logger.info(f"✅ Using default config: {len(self.zones)} zones")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.success(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
            client.subscribe("actuators/irrigation/command")
            client.subscribe("actuators/fertilizer/command")  # NEW
            logger.info("📡 Subscribed to irrigation and fertilizer commands")
        else:
            logger.error(f"❌ Connection failed with code {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Handle irrigation and fertilizer commands"""
        try:
            data = json.loads(msg.payload.decode())
            zone_id = data.get('zone_id')
            
            if 'irrigation' in msg.topic and zone_id in self.zone_state:
                amount_mm = data.get('amount_mm', 0)
                logger.warning(f"💧 IRRIGATION COMMAND RECEIVED for {zone_id}: {amount_mm}mm")
                
                # Simulate moisture increase (10mm = 3% moisture increase)
                moisture_increase = amount_mm * 0.3
                self.zone_state[zone_id]['soil_moisture'] += moisture_increase
                self.zone_state[zone_id]['soil_moisture'] = min(
                    self.zone_state[zone_id]['soil_moisture'], 35.0
                )
                
                # Deduct water from reservoir
                area_m2 = 1000  # Assume 1000 m² per zone
                water_used_liters = (amount_mm / 1000) * area_m2 * 1000
                self.water_reservoir['current_level_liters'] -= water_used_liters
                self.water_reservoir['current_level_liters'] = max(0, self.water_reservoir['current_level_liters'])
                
                logger.success(f"✅ {zone_id} moisture increased to {self.zone_state[zone_id]['soil_moisture']:.1f}%")
                logger.info(f"💦 Water reservoir: {self.water_reservoir['current_level_liters']:.0f}L remaining")
            
            elif 'fertilizer' in msg.topic and zone_id in self.zone_state:
                # NEW: Handle fertilizer application
                nutrient = data.get('nutrient')  # 'N', 'P', or 'K'
                amount_kg = data.get('amount_kg', 0)
                
                logger.warning(f"🌿 FERTILIZER COMMAND RECEIVED for {zone_id}: {amount_kg}kg of {nutrient}")
                
                # Simulate nutrient increase
                nutrient_map = {'N': 'nitrogen', 'P': 'phosphorus', 'K': 'potassium'}
                if nutrient in nutrient_map:
                    nutrient_key = nutrient_map[nutrient]
                    # Convert kg/ha to mg/kg increase (rough approximation)
                    increase = amount_kg * 0.5  # mg/kg per kg/ha
                    self.zone_state[zone_id][nutrient_key] += increase
                    logger.success(f"✅ {zone_id} {nutrient} increased to {self.zone_state[zone_id][nutrient_key]:.1f} mg/kg")
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
    
    def connect(self):
        """Connect to MQTT broker with retry logic"""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to MQTT broker {self.broker}:{self.port} (attempt {attempt + 1}/{max_retries})")
                self.client.connect(self.broker, self.port, keepalive=60)
                self.client.loop_start()
                logger.info("✅ MQTT client loop started")
                return True
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    logger.error("Max connection retries reached")
                    raise
        
        return False
    
    def simulate_environmental_changes(self):
        """Simulate daily environmental cycles and nutrient depletion"""
        # Advance time
        self.hour_of_day = (self.hour_of_day + 1) % 24
        
        # Temperature and humidity (existing code)
        temp_amplitude = 8
        base_temp = 15
        air_temp = base_temp + temp_amplitude * math.sin((self.hour_of_day - 6) * math.pi / 12)
        soil_temp = base_temp + (temp_amplitude * 0.5) * math.sin((self.hour_of_day - 9) * math.pi / 12)
        air_humidity = 70 - (air_temp - base_temp) * 2
        air_humidity = max(30, min(95, air_humidity))
        
        # Random rainfall (5% chance)
        rainfall = 0
        if random.random() < 0.05:
            rainfall = random.uniform(2, 15)
            logger.info(f"🌧️ Rain event: {rainfall:.1f}mm")
            # Rainfall can cause nutrient leaching
        
        # Update all zones
        for zone_id, state in self.zone_state.items():
            # Update environmental values
            state['air_temp'] = air_temp
            state['soil_temp'] = soil_temp
            state['air_humidity'] = air_humidity
            
            # Soil moisture dynamics
            if rainfall > 0:
                moisture_increase = rainfall * 0.25
                state['soil_moisture'] += moisture_increase
                state['soil_moisture'] = min(state['soil_moisture'], 35.0)
                
                # NEW: Rainfall causes nutrient leaching (10-15% loss)
                leaching_factor = rainfall / 100  # More rain = more leaching
                state['nitrogen'] *= (1 - leaching_factor * 0.15)
                state['phosphorus'] *= (1 - leaching_factor * 0.05)  # P leaches less
                state['potassium'] *= (1 - leaching_factor * 0.10)
                logger.info(f"🌧️ {zone_id}: Nutrient leaching due to rain")
            
            # Evapotranspiration
            if self.iteration_count % 2 == 1:
                state['soil_moisture'] -= 2.5
                logger.info(f"🔥 High ET event for {zone_id}: moisture dropping")
            else:
                if 6 <= self.hour_of_day <= 18:
                    et_rate = self.evapotranspiration_rate * (1 + (air_temp - base_temp) / 10)
                    state['soil_moisture'] -= et_rate
                else:
                    state['soil_moisture'] -= self.evapotranspiration_rate * 0.2
            
            state['soil_moisture'] = max(state['soil_moisture'], 18.0)
            
            # NEW: NPK depletion due to plant uptake (slower than moisture)
            # Depletion rate depends on growth stage (simulated by time of day)
            if 6 <= self.hour_of_day <= 18:  # Daytime - active growth
                state['nitrogen'] -= random.uniform(0.3, 0.8)      # N depletes fastest
                state['phosphorus'] -= random.uniform(0.1, 0.3)    # P depletes slower
                state['potassium'] -= random.uniform(0.2, 0.5)     # K intermediate
            
            # Prevent negative values
            state['nitrogen'] = max(state['nitrogen'], 10.0)
            state['phosphorus'] = max(state['phosphorus'], 5.0)
            state['potassium'] = max(state['potassium'], 30.0)
            
            # Log nutrient status
            if state['nitrogen'] < 60:
                logger.warning(f"⚠️  {zone_id} NITROGEN LOW: {state['nitrogen']:.1f} mg/kg")
            if state['phosphorus'] < 30:
                logger.warning(f"⚠️  {zone_id} PHOSPHORUS LOW: {state['phosphorus']:.1f} mg/kg")
            if state['potassium'] < 150:
                logger.warning(f"⚠️  {zone_id} POTASSIUM LOW: {state['potassium']:.1f} mg/kg")
        
        # NEW: Water reservoir refill simulation (slow refill overnight)
        if 0 <= self.hour_of_day <= 6:  # Nighttime refill
            refill_rate = 500 / 6  # liters per hour
            self.water_reservoir['current_level_liters'] += refill_rate
            self.water_reservoir['current_level_liters'] = min(
                self.water_reservoir['current_level_liters'],
                self.water_reservoir['capacity_liters']
            )
    
    def publish_sensor_data(self):
        """Publish sensor readings for all zones + NPK + water level"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        for zone in self.zones:
            zone_id = zone['zone_id']
            state = self.zone_state[zone_id]
            
            # Existing sensors (soil moisture, temperature, etc.)
            moisture_payload = {
                'timestamp': timestamp,
                'zone_id': zone_id,
                'depth_cm': zone.get('depth_cm', 30),
                'value': round(state['soil_moisture'], 2),
                'unit': 'percent'
            }
            self.client.publish('sensors/soil/moisture', json.dumps(moisture_payload))
            
            soil_temp_payload = {
                'timestamp': timestamp,
                'zone_id': zone_id,
                'depth_cm': zone.get('depth_cm', 30),
                'value': round(state['soil_temp'], 2),
                'unit': 'celsius'
            }
            self.client.publish('sensors/soil/temperature', json.dumps(soil_temp_payload))
            
            air_temp_payload = {
                'timestamp': timestamp,
                'zone_id': zone_id,
                'value': round(state['air_temp'], 2),
                'unit': 'celsius'
            }
            self.client.publish('sensors/air/temperature', json.dumps(air_temp_payload))
            
            humidity_payload = {
                'timestamp': timestamp,
                'zone_id': zone_id,
                'value': round(state['air_humidity'], 2),
                'unit': 'percent'
            }
            self.client.publish('sensors/air/humidity', json.dumps(humidity_payload))
            
            # NEW: NPK Sensors
            nitrogen_payload = {
                'timestamp': timestamp,
                'zone_id': zone_id,
                'depth_cm': zone.get('depth_cm', 30),
                'value': round(state['nitrogen'], 2),
                'unit': 'mg/kg',
                'nutrient': 'N'
            }
            self.client.publish('sensors/soil/npk/nitrogen', json.dumps(nitrogen_payload))
            
            phosphorus_payload = {
                'timestamp': timestamp,
                'zone_id': zone_id,
                'depth_cm': zone.get('depth_cm', 30),
                'value': round(state['phosphorus'], 2),
                'unit': 'mg/kg',
                'nutrient': 'P'
            }
            self.client.publish('sensors/soil/npk/phosphorus', json.dumps(phosphorus_payload))
            
            potassium_payload = {
                'timestamp': timestamp,
                'zone_id': zone_id,
                'depth_cm': zone.get('depth_cm', 30),
                'value': round(state['potassium'], 2),
                'unit': 'mg/kg',
                'nutrient': 'K'
            }
            self.client.publish('sensors/soil/npk/potassium', json.dumps(potassium_payload))
            
            # Enhanced logging with NPK
            moisture_emoji = "🔴" if state['soil_moisture'] < 25 else "🟡" if state['soil_moisture'] < 28 else "🟢"
            n_emoji = "🔴" if state['nitrogen'] < 60 else "🟡" if state['nitrogen'] < 80 else "🟢"
            p_emoji = "🔴" if state['phosphorus'] < 30 else "🟡" if state['phosphorus'] < 40 else "🟢"
            k_emoji = "🔴" if state['potassium'] < 150 else "🟡" if state['potassium'] < 180 else "🟢"
            
            logger.info(f"{moisture_emoji} {zone_id}: Moisture={state['soil_moisture']:.1f}%, "
                       f"Temp={state['air_temp']:.1f}°C, "
                       f"Humidity={state['air_humidity']:.1f}% | "
                       f"{n_emoji}N={state['nitrogen']:.1f} "
                       f"{p_emoji}P={state['phosphorus']:.1f} "
                       f"{k_emoji}K={state['potassium']:.1f} mg/kg")
        
        # NEW: Publish water level
        water_level_percent = (self.water_reservoir['current_level_liters'] / 
                               self.water_reservoir['capacity_liters']) * 100
        
        water_level_payload = {
            'timestamp': timestamp,
            'current_liters': round(self.water_reservoir['current_level_liters'], 2),
            'capacity_liters': self.water_reservoir['capacity_liters'],
            'level_percent': round(water_level_percent, 2),
            'unit': 'percent'
        }
        self.client.publish('sensors/water/level', json.dumps(water_level_payload))
        
        water_emoji = "🔴" if water_level_percent < 20 else "🟡" if water_level_percent < 40 else "🟢"
        logger.info(f"{water_emoji} 💦 Water Reservoir: {water_level_percent:.1f}% "
                   f"({self.water_reservoir['current_level_liters']:.0f}L / "
                   f"{self.water_reservoir['capacity_liters']:.0f}L)")
    
    def run(self):
        """Main simulation loop"""
        logger.info("🌱 Starting Mock Sensor Data Generator with NPK & Water Level")
        logger.info(f"Monitoring {len(self.zones)} zones: {[z['zone_id'] for z in self.zones]}")
        logger.info("🎯 Configured to trigger irrigation every 2 iterations")
        logger.info("🌿 Monitoring: Moisture, Temp, Humidity, N, P, K, Water Level")
        
        # Connect to MQTT
        if not self.connect():
            logger.error("Failed to connect to MQTT broker")
            return
        
        # Wait for connection to stabilize
        time.sleep(3)
        
        sensor_interval = int(os.getenv('SENSOR_INTERVAL', 30))
        
        logger.info(f"⏱️  Publishing sensor data every {sensor_interval} seconds")
        logger.info(f"💧 Irrigation threshold: moisture < 25% (PAW < 50%)")
        logger.info(f"🌿 NPK thresholds: N<60, P<30, K<150 mg/kg")
        
        while True:
            try:
                self.iteration_count += 1
                logger.info(f"\n{'='*70}")
                logger.info(f"Iteration {self.iteration_count} | Hour {self.hour_of_day}:00")
                logger.info(f"{'='*70}")
                
                # Simulate environmental changes
                self.simulate_environmental_changes()
                
                # Publish sensor data
                self.publish_sensor_data()
                
                # Wait before next reading
                time.sleep(sensor_interval)
                
            except KeyboardInterrupt:
                logger.info("\n⏹️  Shutting down...")
                self.client.loop_stop()
                self.client.disconnect()
                break
            except Exception as e:
                logger.error(f"❌ Error in simulation loop: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)


if __name__ == '__main__':
    # Configure logger
    logger.remove()
    logger.add(sys.stdout, 
               format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
               level="INFO")
    
    # Create and run generator
    try:
        generator = MockSensorGenerator()
        generator.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)