from datetime import datetime, timedelta, timezone
from loguru import logger

class SoilAnalyzer:
    def __init__(self, soil_config, db_manager):
        self.config = soil_config
        self.db = db_manager
        self.last_irrigation = {}
    
    def analyze_moisture(self, zone_id, current_moisture_pct):
        field_capacity = 33.0
        wilting_point = 12.0
        
        if current_moisture_pct <= wilting_point:
            paw_pct = 0
        elif current_moisture_pct >= field_capacity:
            paw_pct = 100
        else:
            paw_pct = ((current_moisture_pct - wilting_point) / 
                      (field_capacity - wilting_point)) * 100
        
        if paw_pct < 30:
            status = "CRITICAL"
        elif paw_pct < 50:
            status = "LOW"
        elif paw_pct < 70:
            status = "ADEQUATE"
        else:
            status = "OPTIMAL"
        
        irrigation_config = self.config['irrigation']
        threshold = irrigation_config['threshold_paw_percentage']
        irrigation_needed = paw_pct < threshold and self._can_irrigate(zone_id, irrigation_config)
        
        recommended_amount = irrigation_config['application_rate_mm'] if irrigation_needed else 0
        
        return {
            'current_moisture_pct': current_moisture_pct,
            'paw_percentage': paw_pct,
            'field_capacity': field_capacity,
            'wilting_point': wilting_point,
            'status': status,
            'irrigation_needed': irrigation_needed,
            'recommended_amount_mm': recommended_amount
        }
    
    def _can_irrigate(self, zone_id, irrigation_config):
        if zone_id not in self.last_irrigation:
            self.last_irrigation[zone_id] = datetime.now(timezone.utc)
            return True
        
        min_interval = timedelta(hours=irrigation_config['min_interval_hours'])
        time_since_last = datetime.now(timezone.utc) - self.last_irrigation[zone_id]
        
        can_irrigate = time_since_last >= min_interval
        
        if can_irrigate:
            self.last_irrigation[zone_id] = datetime.now(timezone.utc)
        
        return can_irrigate
