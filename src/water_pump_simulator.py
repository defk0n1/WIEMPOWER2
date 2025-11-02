"""
Water Pump Simulator
Simulates water pump activation and soil moisture changes
"""

from typing import Dict, Optional
from datetime import datetime
from loguru import logger
import json


class WaterPumpSimulator:
    """Simulates water pump and soil moisture dynamics"""
    
    def __init__(self, pump_flow_rate_lpm: float = 20.0, area_sqm: float = 100.0):
        """
        Initialize Water Pump Simulator
        
        Args:
            pump_flow_rate_lpm: Pump flow rate in liters per minute
            area_sqm: Irrigation area in square meters
        """
        self.pump_flow_rate_lpm = pump_flow_rate_lpm
        self.area_sqm = area_sqm
        self.is_running = False
        self.total_water_dispensed_liters = 0.0
        
        logger.info(f"💧 Water Pump initialized: {pump_flow_rate_lpm}L/min, Area: {area_sqm}m²")
    
    def activate(self, amount_mm: float, zone_id: str) -> Dict:
        """
        Activate water pump to dispense specified amount
        
        Args:
            amount_mm: Water amount in millimeters
            zone_id: Zone identifier
            
        Returns:
            Dictionary with pump activation details
        """
        if amount_mm <= 0:
            logger.warning(f"⚠️  Invalid irrigation amount: {amount_mm}mm")
            return self._create_result(False, 0, 0, zone_id, "Invalid amount")
        
        # Calculate water volume needed
        # 1mm over 1m² = 1 liter
        volume_liters = amount_mm * self.area_sqm
        
        # Calculate duration
        duration_minutes = volume_liters / self.pump_flow_rate_lpm
        
        # Simulate pump activation
        self.is_running = True
        logger.info(f"🚿 PUMP ACTIVATED: Zone {zone_id}, {amount_mm}mm ({volume_liters:.1f}L), Duration: {duration_minutes:.1f}min")
        
        # Update total
        self.total_water_dispensed_liters += volume_liters
        
        # Simulate completion
        self.is_running = False
        
        return self._create_result(
            success=True,
            volume_liters=volume_liters,
            duration_minutes=duration_minutes,
            zone_id=zone_id,
            status="Completed successfully"
        )
    
    def calculate_moisture_increase(self, 
                                   current_moisture: float, 
                                   water_mm: float,
                                   soil_type: str = "loam") -> float:
        """
        Calculate new moisture level after irrigation
        
        Args:
            current_moisture: Current soil moisture percentage
            water_mm: Water applied in millimeters
            soil_type: Soil type (sand, loam, clay)
            
        Returns:
            New moisture percentage
        """
        # Soil absorption coefficients (simplified)
        absorption_rates = {
            'sand': 0.3,    # Low water retention
            'loam': 0.5,    # Medium retention
            'clay': 0.7     # High retention
        }
        
        absorption = absorption_rates.get(soil_type, 0.5)
        
        # Calculate moisture increase
        # Simplified: 10mm of water ≈ 5% moisture increase for loam
        moisture_increase = (water_mm / 10) * 5 * absorption
        
        # Calculate new moisture (capped at 100%)
        new_moisture = min(current_moisture + moisture_increase, 100.0)
        
        logger.debug(f"💦 Moisture change: {current_moisture:.1f}% → {new_moisture:.1f}% "
                    f"(+{moisture_increase:.1f}% from {water_mm}mm)")
        
        return round(new_moisture, 2)
    
    def _create_result(self, success: bool, volume_liters: float, 
                      duration_minutes: float, zone_id: str, status: str) -> Dict:
        """Create pump activation result"""
        return {
            'success': success,
            'zone_id': zone_id,
            'volume_liters': round(volume_liters, 2),
            'duration_minutes': round(duration_minutes, 2),
            'timestamp': datetime.utcnow().isoformat(),
            'status': status,
            'total_dispensed_liters': round(self.total_water_dispensed_liters, 2)
        }
    
    def get_status(self) -> Dict:
        """Get current pump status"""
        return {
            'is_running': self.is_running,
            'total_dispensed_liters': round(self.total_water_dispensed_liters, 2),
            'flow_rate_lpm': self.pump_flow_rate_lpm,
            'area_sqm': self.area_sqm
        }