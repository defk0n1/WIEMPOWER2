"""
Irrigation Job Scheduler
Publishes all events to MQTT for mobile app consumption
"""

import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from loguru import logger
import json

from data_storage import DatabaseManager, SensorReading, NPKReading, HumidityReading
from pump_model_client import PumpModelClient, MockMLModelService
from water_pump_simulator import WaterPumpSimulator


class IrrigationJob:
    """Scheduled job for automated irrigation decisions"""
    
    def __init__(self, 
                 db_manager: DatabaseManager,
                 mqtt_client,
                 ml_model_url: Optional[str] = None,
                 interval_minutes: int = 30,
                 use_mock_model: bool = True):
        """Initialize Irrigation Job"""
        self.db_manager = db_manager
        self.mqtt_client = mqtt_client
        self.interval_minutes = interval_minutes
        self.use_mock_model = use_mock_model
        
        # Initialize ML client
        if use_mock_model:
            logger.info("🤖 Using MOCK ML Model (local)")
            self.ml_client = None
        else:
            self.ml_client = PumpModelClient(ml_model_url or "http://ml-service:8000/predict")
        
        # Initialize water pump simulator
        self.pump = WaterPumpSimulator(pump_flow_rate_lpm=20.0, area_sqm=100.0)
        
        # Job control
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.execution_count = 0
        self.last_execution: Optional[datetime] = None
        
        logger.info(f"⏰ Irrigation Job initialized: Interval={interval_minutes} minutes")
    
    def set_mqtt_client(self, mqtt_client):
        """Set or update MQTT client"""
        self.mqtt_client = mqtt_client
        logger.info("✅ MQTT client set for irrigation job")
    
    def start(self):
        """Start the irrigation job"""
        if self.running:
            logger.warning("⚠️  Irrigation job already running")
            return
        
        if not self.mqtt_client:
            logger.warning("⚠️  MQTT client not set - some features may not work")
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"🚀 Irrigation Job started (every {self.interval_minutes} minutes)")
        
        # Publish job started event
        self._publish_job_event("job_started", {
            "interval_minutes": self.interval_minutes,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def stop(self):
        """Stop the irrigation job"""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        # Publish job stopped event
        self._publish_job_event("job_stopped", {
            "total_executions": self.execution_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        logger.info("⏹️  Irrigation Job stopped")
    
    def _run_loop(self):
        """Main job execution loop"""
        while self.running:
            try:
                self.execute()
                
                # Sleep for interval
                sleep_seconds = self.interval_minutes * 60
                for _ in range(sleep_seconds):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Error in irrigation job loop: {e}")
                import traceback
                traceback.print_exc()
                
                # Publish error event
                self._publish_job_event("job_error", {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                time.sleep(60)
    
    def execute(self):
        """Execute one iteration of the irrigation job"""
        self.execution_count += 1
        self.last_execution = datetime.now(timezone.utc)
        
        logger.info("="*60)
        logger.info(f"🔄 IRRIGATION JOB EXECUTION #{self.execution_count}")
        logger.info(f"⏰ Time: {self.last_execution.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("="*60)
        
        # Publish job execution started event
        self._publish_job_event("execution_started", {
            "execution_number": self.execution_count,
            "timestamp": self.last_execution.isoformat()
        })
        
        # Get all zones
        zones = self._get_active_zones()
        
        if not zones:
            logger.warning("⚠️  No active zones found")
            self._publish_job_event("no_zones_found", {
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return
        
        logger.info(f"📍 Evaluating {len(zones)} zone(s): {', '.join(zones)}")
        
        # Publish zones being evaluated
        self._publish_job_event("zones_evaluation", {
            "zones": zones,
            "count": len(zones),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Process each zone
        results = []
        for zone_id in zones:
            try:
                result = self._process_zone(zone_id)
                results.append(result)
            except Exception as e:
                logger.error(f"❌ Error processing zone {zone_id}: {e}")
                import traceback
                traceback.print_exc()
                
                # Publish zone error
                self._publish_zone_event(zone_id, "zone_error", {
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        
        logger.info("="*60)
        logger.info(f"✅ Job execution completed. Next run in {self.interval_minutes} minutes")
        logger.info("="*60)
        
        # Publish execution completed event
        self._publish_job_event("execution_completed", {
            "execution_number": self.execution_count,
            "zones_processed": len(results),
            "irrigations_performed": sum(1 for r in results if r.get('irrigated')),
            "next_run": (self.last_execution + timedelta(minutes=self.interval_minutes)).isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    def _get_active_zones(self) -> list:
        """Get list of active zones from database"""
        session = self.db_manager.get_session()
        try:
            from sqlalchemy import func, distinct
            
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            recent_zones = session.query(distinct(SensorReading.zone_id)).filter(
                SensorReading.sensor_type == 'moisture',
                SensorReading.timestamp >= cutoff_time,
                SensorReading.zone_id.isnot(None),
                SensorReading.zone_id != 'N/A'
            ).limit(10).all()
            
            zones = [z[0] for z in recent_zones if z[0]]
            
            if not zones:
                logger.info("   No zones with recent data, using default: zone-1")
                zones = ['zone-1']
            
            return zones
            
        finally:
            session.close()
    
    def _process_zone(self, zone_id: str) -> Dict:
        """Process irrigation decision for a single zone"""
        logger.info(f"\n{'─'*60}")
        logger.info(f"🌱 Processing Zone: {zone_id}")
        logger.info(f"{'─'*60}")
        
        result = {
            "zone_id": zone_id,
            "irrigated": False,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Step 1: Gather current metrics
        metrics = self._gather_metrics(zone_id)
        
        if not metrics:
            logger.warning(f"⚠️  No metrics available for {zone_id}")
            self._publish_zone_event(zone_id, "no_metrics", {
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return result
        
        logger.info(f"📊 Current Metrics:")
        logger.info(f"   💦 Moisture: {metrics.get('moisture_percent', 'N/A')}%")
        logger.info(f"   🌡️  Temperature: {metrics.get('temperature_celsius', 'N/A')}°C")
        logger.info(f"   🌫️  Humidity: {metrics.get('humidity_percent', 'N/A')}%")
        logger.info(f"   🌿 NPK Status: {metrics.get('npk_status', 'N/A')}")
        
        # Publish metrics gathered event
        self._publish_zone_event(zone_id, "metrics_gathered", metrics)
        
        # Step 2: Get ML model decision
        if self.use_mock_model:
            decision = MockMLModelService.predict(metrics)
        else:
            decision = self.ml_client.predict_irrigation(metrics)
        
        logger.info(f"\n🤖 ML Model Decision:")
        logger.info(f"   Should Irrigate: {decision['should_irrigate']}")
        logger.info(f"   Confidence: {decision['confidence']:.1%}")
        logger.info(f"   Recommended Amount: {decision['recommended_amount_mm']}mm")
        logger.info(f"   Reason: {decision['reason']}")
        
        # Publish ML decision event
        self._publish_zone_event(zone_id, "ml_decision", decision)
        
        result['decision'] = decision
        
        # Step 3: Execute irrigation if needed
        if decision['should_irrigate']:
            irrigation_result = self._execute_irrigation(zone_id, decision, metrics)
            result['irrigated'] = irrigation_result.get('success', False)
            result['irrigation'] = irrigation_result
        else:
            logger.info(f"✅ {zone_id}: No irrigation needed - {decision['reason']}")
            self._publish_zone_event(zone_id, "irrigation_skipped", {
                "reason": decision['reason'],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        return result
    
    def _gather_metrics(self, zone_id: str) -> Optional[Dict]:
        """Gather current metrics for a zone"""
        session = self.db_manager.get_session()
        
        try:
            from sqlalchemy import desc
            
            metrics = {}
            
            # Get latest moisture
            moisture = session.query(SensorReading).filter(
                SensorReading.zone_id == zone_id,
                SensorReading.sensor_type == 'moisture'
            ).order_by(desc(SensorReading.timestamp)).first()
            
            if moisture:
                metrics['moisture_percent'] = moisture.value
            else:
                logger.warning(f"⚠️  No moisture data for {zone_id}")
                return None
            
            # Get latest temperature
            temperature = session.query(SensorReading).filter(
                SensorReading.zone_id == zone_id,
                SensorReading.sensor_type == 'temperature'
            ).order_by(desc(SensorReading.timestamp)).first()
            
            metrics['temperature_celsius'] = temperature.value if temperature else 25.0
            
            # Get latest humidity
            humidity = session.query(HumidityReading).filter(
                HumidityReading.zone_id == zone_id
            ).order_by(desc(HumidityReading.timestamp)).first()
            
            metrics['humidity_percent'] = humidity.humidity if humidity else 60.0
            
            # Get latest NPK
            npk = session.query(NPKReading).filter(
                NPKReading.zone_id == zone_id
            ).order_by(desc(NPKReading.timestamp)).first()
            
            if npk:
                metrics['nitrogen_mgkg'] = npk.nitrogen
                metrics['phosphorus_mgkg'] = npk.phosphorus
                metrics['potassium_mgkg'] = npk.potassium
                
                if npk.nitrogen < 40 or npk.phosphorus < 25 or npk.potassium < 100:
                    metrics['npk_status'] = 'LOW'
                elif npk.nitrogen > 80 and npk.phosphorus > 40 and npk.potassium > 150:
                    metrics['npk_status'] = 'OPTIMAL'
                else:
                    metrics['npk_status'] = 'ADEQUATE'
            else:
                metrics['npk_status'] = 'UNKNOWN'
            
            metrics['rainfall_mm_24h'] = 0.0
            metrics['zone_id'] = zone_id
            metrics['timestamp'] = datetime.utcnow().isoformat()
            
            return metrics
            
        finally:
            session.close()
    
    def _execute_irrigation(self, zone_id: str, decision: Dict, metrics: Dict) -> Dict:
        """Execute irrigation and update metrics"""
        amount_mm = decision['recommended_amount_mm']
        
        logger.info(f"\n💧 EXECUTING IRRIGATION:")
        logger.info(f"   Zone: {zone_id}")
        logger.info(f"   Amount: {amount_mm}mm")
        logger.info(f"   Confidence: {decision['confidence']:.1%}")
        
        # Publish irrigation started event
        self._publish_irrigation_event(zone_id, "irrigation_started", {
            "amount_mm": amount_mm,
            "confidence": decision['confidence'],
            "reason": decision['reason'],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Step 1: Activate water pump
        pump_result = self.pump.activate(amount_mm, zone_id)
        
        irrigation_result = {
            "success": pump_result['success'],
            "zone_id": zone_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if pump_result['success']:
            logger.info(f"   ✅ Pump activated successfully")
            logger.info(f"   ⏱️  Duration: {pump_result['duration_minutes']:.1f} minutes")
            logger.info(f"   💧 Volume dispensed: {pump_result['volume_liters']:.1f}L")
            
            # Step 2: Calculate new moisture
            current_moisture = metrics['moisture_percent']
            new_moisture = self.pump.calculate_moisture_increase(
                current_moisture=current_moisture,
                water_mm=amount_mm,
                soil_type='loam'
            )
            
            logger.info(f"   📈 Moisture update: {current_moisture:.1f}% → {new_moisture:.1f}%")
            
            irrigation_result.update({
                "duration_minutes": pump_result['duration_minutes'],
                "volume_liters": pump_result['volume_liters'],
                "moisture_before": current_moisture,
                "moisture_after": new_moisture,
                "amount_mm": amount_mm
            })
            
            # Step 3: Publish updated moisture
            if self.mqtt_client:
                self._publish_updated_moisture(zone_id, new_moisture)
            
            # Step 4: Store irrigation event
            self._store_irrigation_event(zone_id, amount_mm, decision, pump_result)
            
            # Step 5: Publish pump command
            if self.mqtt_client:
                self._publish_pump_command(zone_id, pump_result, decision)
            
            # Step 6: Publish irrigation completed event
            self._publish_irrigation_event(zone_id, "irrigation_completed", irrigation_result)
            
            logger.info(f"   ✅ Irrigation completed for {zone_id}")
            
        else:
            logger.error(f"   ❌ Pump activation failed: {pump_result['status']}")
            irrigation_result['error'] = pump_result['status']
            
            # Publish irrigation failed event
            self._publish_irrigation_event(zone_id, "irrigation_failed", irrigation_result)
        
        return irrigation_result
    
    def _publish_updated_moisture(self, zone_id: str, new_moisture: float):
        """Publish updated moisture reading to MQTT"""
        if not self.mqtt_client:
            logger.warning(f"   ⚠️  MQTT client not available")
            return
        
        payload = {
            'zone_id': zone_id,
            'value': new_moisture,
            'unit': '%',
            'sensor_id': 'moisture-simulator',
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'irrigation_job'
        }
        
        try:
            result = self.mqtt_client.publish('sensors/soil/moisture', json.dumps(payload), qos=1)
            if hasattr(result, 'rc') and result.rc == 0:
                logger.debug(f"   📤 Published updated moisture: {new_moisture:.1f}%")
        except Exception as e:
            logger.error(f"   ❌ Error publishing moisture: {e}")
    
    def _store_irrigation_event(self, zone_id: str, amount_mm: float, 
                                decision: Dict, pump_result: Dict):
        """Store irrigation event in database"""
        try:
            reason = f"ML: {decision['reason']} (Confidence: {decision['confidence']:.1%})"
            
            self.db_manager.store_irrigation_event(
                timestamp=datetime.utcnow(),
                zone_id=zone_id,
                amount_mm=amount_mm,
                automated=True,
                reason=reason
            )
            logger.debug(f"   💾 Stored irrigation event in database")
        except Exception as e:
            logger.error(f"   ❌ Failed to store irrigation event: {e}")
    
    def _publish_pump_command(self, zone_id: str, pump_result: Dict, decision: Dict):
        """Publish pump activation command to MQTT"""
        if not self.mqtt_client:
            logger.warning(f"   ⚠️  MQTT client not available")
            return
        
        command = {
            'zone_id': zone_id,
            'action': 'activate',
            'duration_minutes': pump_result['duration_minutes'],
            'volume_liters': pump_result['volume_liters'],
            'timestamp': pump_result['timestamp'],
            'automated': True,
            'ml_decision': {
                'confidence': decision['confidence'],
                'reason': decision['reason'],
                'model_version': decision['model_version']
            }
        }
        
        try:
            result = self.mqtt_client.publish('actuators/pump/command', json.dumps(command), qos=1)
            if hasattr(result, 'rc') and result.rc == 0:
                logger.debug(f"   📤 Published pump command")
        except Exception as e:
            logger.error(f"   ❌ Error publishing pump command: {e}")
    
    # ==================== MQTT Event Publishing Methods ====================
    
    def _publish_job_event(self, event_type: str, data: Dict):
        """Publish irrigation job event to MQTT"""
        if not self.mqtt_client:
            return
        
        topic = f"irrigation/job/{event_type}"
        payload = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            result = self.mqtt_client.publish(topic, json.dumps(payload), qos=1)
            if hasattr(result, 'rc') and result.rc == 0:
                logger.debug(f"📤 Published job event: {event_type}")
        except Exception as e:
            logger.error(f"❌ Error publishing job event: {e}")
    
    def _publish_zone_event(self, zone_id: str, event_type: str, data: Dict):
        """Publish zone-specific event to MQTT"""
        if not self.mqtt_client:
            return
        
        topic = f"irrigation/zones/{zone_id}/{event_type}"
        payload = {
            "zone_id": zone_id,
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            result = self.mqtt_client.publish(topic, json.dumps(payload), qos=1)
            if hasattr(result, 'rc') and result.rc == 0:
                logger.debug(f"📤 Published zone event: {zone_id}/{event_type}")
        except Exception as e:
            logger.error(f"❌ Error publishing zone event: {e}")
    
    def _publish_irrigation_event(self, zone_id: str, event_type: str, data: Dict):
        """Publish irrigation-specific event to MQTT"""
        if not self.mqtt_client:
            return
        
        topic = f"irrigation/events/{zone_id}/{event_type}"
        payload = {
            "zone_id": zone_id,
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            result = self.mqtt_client.publish(topic, json.dumps(payload), qos=1)
            if hasattr(result, 'rc') and result.rc == 0:
                logger.debug(f"📤 Published irrigation event: {zone_id}/{event_type}")
        except Exception as e:
            logger.error(f"❌ Error publishing irrigation event: {e}")
    
    def get_status(self) -> Dict:
        """Get current job status"""
        return {
            'running': self.running,
            'interval_minutes': self.interval_minutes,
            'execution_count': self.execution_count,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'mqtt_connected': self.mqtt_client is not None,
            'pump_status': self.pump.get_status()
        }