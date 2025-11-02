"""
Irrigation recommendation and prediction engine
"""

import json
from datetime import datetime, timezone, timedelta
from loguru import logger
import paho.mqtt.client as mqtt


class IrrigationController:
    """Control and automate irrigation based on predictions"""
    
    def __init__(self, mqtt_broker, mqtt_port, db_manager, soil_analyzer, mqtt_client=None):
        """Initialize irrigation controller"""
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.db = db_manager
        self.analyzer = soil_analyzer
        self.mqtt_client = mqtt_client  # Reuse existing MQTT client
        self.last_irrigation = {}  # Track last irrigation per zone
        self.iteration_counter = {}  # Track iterations per zone for forced irrigation
        
        logger.info("🚿 Irrigation Controller initialized")
    
    def connect_mqtt(self):
        """Connect to MQTT broker for sending commands"""
        if self.mqtt_client is not None:
            logger.info("✅ Using existing MQTT client connection")
            return
        
        # Only create new client if one wasn't provided
        self.mqtt_client = mqtt.Client(
            client_id="irrigation_controller_" + str(int(datetime.now().timestamp())),
            clean_session=True
        )
        
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
            logger.info("✅ Irrigation controller connected to MQTT")
        except Exception as e:
            logger.error(f"❌ Failed to connect irrigation controller to MQTT: {e}")
    
    def should_irrigate(self, zone_id, analysis, force=False):
        """Determine if irrigation should be triggered"""
        
        # Initialize iteration counter for this zone if not exists
        if zone_id not in self.iteration_counter:
            self.iteration_counter[zone_id] = 0
        
        # Increment iteration counter
        self.iteration_counter[zone_id] += 1
        
        # Force irrigation every 3rd iteration
        if self.iteration_counter[zone_id] % 3 == 0:
            logger.warning(f"🔄 {zone_id}: Forced irrigation on iteration {self.iteration_counter[zone_id]}")
            return True
        
        # If forced, skip other checks
        if force:
            return True
        
        # Normal irrigation logic
        if not analysis.get('irrigation_needed', False):
            return False
        
        # Check minimum interval
        if zone_id in self.last_irrigation:
            time_since_last = datetime.now(timezone.utc) - self.last_irrigation[zone_id]
            min_interval_hours = self.analyzer.config.get('irrigation', {}).get('min_interval_hours', 6)
            min_interval = timedelta(hours=min_interval_hours)
            
            if time_since_last < min_interval:
                hours_remaining = (min_interval - time_since_last).total_seconds() / 3600
                logger.info(f"⏳ {zone_id}: Too soon since last irrigation ({hours_remaining:.1f}h remaining)")
                return False
        
        return True
    
    def trigger_irrigation(self, zone_id, amount_mm, automated=True, reason=None):
        """Trigger irrigation event"""
        timestamp = datetime.now(timezone.utc)
        
        # Send MQTT command
        command = {
            'zone_id': zone_id,
            'amount_mm': amount_mm,
            'timestamp': timestamp.isoformat(),
            'automated': automated
        }
        
        if self.mqtt_client:
            topic = "actuators/irrigation/command"
            try:
                result = self.mqtt_client.publish(topic, json.dumps(command))
                logger.warning(f"💧 IRRIGATION TRIGGERED: {zone_id} → {amount_mm}mm (automated={automated})")
            except Exception as e:
                logger.error(f"❌ Failed to publish irrigation command: {e}")
        else:
            logger.error("❌ No MQTT client available to send irrigation command")
        
        # Log to database
        if not reason:
            iteration = self.iteration_counter.get(zone_id, 0)
            if iteration % 3 == 0:
                reason = f"Forced irrigation (iteration {iteration})"
            else:
                threshold = self.analyzer.config.get('irrigation', {}).get('threshold_paw_percentage', 50)
                reason = f"PAW below threshold ({threshold}%)"
        
        self.db.store_irrigation_event(
            timestamp=timestamp,
            zone_id=zone_id,
            amount_mm=amount_mm,
            automated=automated,
            reason=reason
        )
        
        # Update last irrigation time
        self.last_irrigation[zone_id] = timestamp
        
        logger.info(f"📊 {zone_id} irrigation stats: Total iterations={self.iteration_counter.get(zone_id, 0)}")
    
    def process_analysis(self, analysis):
        """Process analysis and make irrigation decision"""
        zone_id = analysis.get('zone_id')
        if not zone_id:
            logger.error("❌ Analysis missing zone_id")
            return
        
        timestamp = analysis.get('timestamp', datetime.now(timezone.utc))
        
        # Store analysis
        self.db.store_soil_analysis(
            timestamp=timestamp,
            zone_id=zone_id,
            paw_percentage=analysis.get('paw_percentage', 0),
            irrigation_needed=analysis.get('irrigation_needed', False),
            current_moisture=analysis.get('current_moisture_pct', 0),
            field_capacity=analysis.get('field_capacity', None),
            wilting_point=analysis.get('wilting_point', None)
        )
        
        # Check if automated irrigation should trigger
        if self.should_irrigate(zone_id, analysis):
            recommended_amount = analysis.get('recommended_amount_mm', 
                                             self.analyzer.config.get('irrigation', {}).get('application_rate_mm', 10))
            self.trigger_irrigation(
                zone_id=zone_id,
                amount_mm=recommended_amount,
                automated=True
            )
        else:
            iteration = self.iteration_counter.get(zone_id, 0)
            logger.debug(f"✅ {zone_id}: No irrigation needed (iteration {iteration}/3)")