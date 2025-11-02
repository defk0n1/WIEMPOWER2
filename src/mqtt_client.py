import os
import json
import yaml
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from loguru import logger
from src.data_storage import DatabaseManager


class SensorDataCollector:
    """MQTT client for collecting sensor data"""
    
    def __init__(self, broker=None, port=None, topics=None, on_message_callback=None, config_path="config/mqtt_config.yaml", db_manager=None):
        """Initialize MQTT client"""
        
        if broker and port and topics:
            self.broker = broker
            self.port = port
            self.topics = topics
            self.custom_callback = on_message_callback
            self.client_id = "irrigation_collector"
        else:
            self.load_config(config_path)
            self.custom_callback = None
        
        self.db = db_manager or DatabaseManager()
        self.client = None
        self.connected = False
        
        logger.info("📡 Sensor Data Collector initialized")
    
    def load_config(self, config_path):
        """Load MQTT configuration"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.broker = os.getenv('MQTT_BROKER', config['mqtt']['broker'])
        self.port = int(os.getenv('MQTT_PORT', config['mqtt']['port']))
        self.client_id = config['mqtt'].get('client_id', 'irrigation_collector')
        self.topics = config['topics']
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.success(f"✅ Connected to MQTT Broker at {self.broker}:{self.port}")
            self.connected = True
            
            # Subscribe to ALL topics with 'sensors' in the path
            subscribed_count = 0
            for topic_name, topic_path in self.topics.items():
                if 'sensors' in topic_path:
                    result = client.subscribe(topic_path)
                    logger.info(f"📥 Subscribed to: {topic_path} (result: {result})")
                    subscribed_count += 1
            
            if subscribed_count == 0:
                logger.warning("⚠️  No sensor topics found to subscribe to!")
                logger.info(f"Available topics: {self.topics}")
        else:
            logger.error(f"❌ Connection failed, return code {rc}")
            self.connected = False
    
    def on_message(self, client, userdata, msg):
        """Handle incoming sensor messages"""
        logger.debug(f"📨 Raw message received on {msg.topic}")
        
        # If custom callback is set, use it
        if self.custom_callback:
            self.custom_callback(client, userdata, msg)
            return
        
        # Default behavior - store in database
        try:
            payload = json.loads(msg.payload.decode())
            timestamp_str = payload.get('timestamp')
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            zone_id = payload.get('zone_id')
            value = payload.get('value')
            unit = payload.get('unit')
            depth_cm = payload.get('depth_cm')
            sensor_type = msg.topic.split('/')[-1]
            
            self.db.store_sensor_reading(
                timestamp=timestamp,
                zone_id=zone_id,
                sensor_type=sensor_type,
                value=value,
                unit=unit,
                depth_cm=depth_cm
            )
            
            logger.debug(f"📥 {sensor_type} from {zone_id}: {value}{unit}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
    
    def connect(self):
        """Connect to MQTT broker"""
        # Create client with proper client_id and keepalive
        self.client = mqtt.Client(client_id=self.client_id, clean_session=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # Enable reconnection
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
        
        try:
            logger.info(f"🔌 Connecting to {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            logger.info("✅ MQTT client loop started")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise
    
    def publish(self, topic, payload):
        """Publish message to MQTT topic"""
        self.client.publish(topic, payload)
        logger.info(f"📤 Published to {topic}")
    
    def stop(self):
        """Stop MQTT client"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        logger.info("⏹️  MQTT client stopped")
    
    def disconnect(self):
        """Alias for stop"""
        self.stop()