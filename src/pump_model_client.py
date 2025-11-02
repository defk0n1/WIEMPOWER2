import requests
import json
from typing import Dict, Optional
from loguru import logger
from datetime import datetime


class PumpModelClient:
    """Client for ML-based irrigation decision service"""
    
    def __init__(self, model_url: str, timeout: int = 10):
        """
        Initialize ML Model Client
        
        Args:
            model_url: URL of the ML model service (e.g., http://ml-service:5000/predict)
            timeout: Request timeout in seconds
        """
        self.model_url = model_url
        self.timeout = timeout
        logger.info(f"🤖 ML Model Client initialized: {model_url}")
    
    def predict_irrigation(self, metrics: Dict) -> Dict:
        """
        Send metrics to ML model and get irrigation decision
        
        Args:
            metrics: Dictionary containing current sensor metrics
            
        Returns:
            Dict with keys:
                - should_irrigate: bool
                - confidence: float (0-1)
                - recommended_amount_mm: float
                - reason: str
                - model_version: str
        """
        try:
            logger.debug(f"📤 Sending metrics to ML model: {metrics}")
            
            response = requests.post(
                self.model_url,
                json=metrics,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ ML Model Response: irrigate={result.get('should_irrigate')}, "
                          f"confidence={result.get('confidence', 0):.2f}, "
                          f"amount={result.get('recommended_amount_mm', 0)}mm")
                return result
            else:
                logger.error(f"❌ ML Model error: {response.status_code} - {response.text}")
                return self._fallback_decision(metrics)
                
        except requests.exceptions.Timeout:
            logger.error(f"⏱️  ML Model request timeout ({self.timeout}s)")
            return self._fallback_decision(metrics)
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 Cannot connect to ML Model service at {self.model_url}")
            return self._fallback_decision(metrics)
        except Exception as e:
            logger.error(f"❌ ML Model prediction error: {e}")
            return self._fallback_decision(metrics)
    
    def _fallback_decision(self, metrics: Dict) -> Dict:
        """
        Fallback rule-based decision if ML model is unavailable
        
        Args:
            metrics: Current metrics
            
        Returns:
            Decision dictionary
        """
        logger.warning("⚠️  Using fallback rule-based decision")
        
        moisture = metrics.get('moisture_percent', 50)
        temperature = metrics.get('temperature_celsius', 25)
        humidity = metrics.get('humidity_percent', 60)
        
        # Simple rule-based logic
        should_irrigate = False
        amount = 0.0
        reason = "Fallback: "
        
        if moisture < 30:
            should_irrigate = True
            amount = 15.0
            reason += "Critical moisture level"
        elif moisture < 40 and temperature > 30:
            should_irrigate = True
            amount = 10.0
            reason += "Low moisture with high temperature"
        elif moisture < 45 and humidity < 30:
            should_irrigate = True
            amount = 8.0
            reason += "Low moisture with low humidity"
        else:
            reason += "Moisture levels adequate"
        
        return {
            'should_irrigate': should_irrigate,
            'confidence': 0.5,  # Low confidence for fallback
            'recommended_amount_mm': amount,
            'reason': reason,
            'model_version': 'fallback-v1.0'
        }


class MockMLModelService:
    """Mock ML Model Service for testing (runs locally)"""
    
    @staticmethod
    def predict(metrics: Dict) -> Dict:
        """
        Mock prediction logic
        
        This simulates an ML model decision based on multiple factors
        """
        moisture = metrics.get('moisture_percent', 50)
        temperature = metrics.get('temperature_celsius', 25)
        humidity = metrics.get('humidity_percent', 60)
        rainfall = metrics.get('rainfall_mm_24h', 0)
        npk_status = metrics.get('npk_status', 'OPTIMAL')
        
        # Calculate weighted score
        moisture_score = (100 - moisture) / 100  # Higher score for lower moisture
        temp_score = max(0, (temperature - 25) / 20)  # Higher score for higher temp
        humidity_score = (100 - humidity) / 100  # Higher score for lower humidity
        rainfall_score = max(0, (10 - rainfall) / 10)  # Lower score if recent rain
        
        # Weighted decision
        irrigation_score = (
            moisture_score * 0.4 +
            temp_score * 0.2 +
            humidity_score * 0.2 +
            rainfall_score * 0.2
        )
        
        should_irrigate = irrigation_score > 0.5
        confidence = min(irrigation_score, 1.0)
        
        # Calculate recommended amount
        if should_irrigate:
            base_amount = 10.0
            amount = base_amount * (1 + moisture_score)
            
            # Adjust for NPK
            if npk_status in ['CRITICAL', 'LOW']:
                amount *= 0.8  # Reduce water if nutrients are low
        else:
            amount = 0.0
        
        # Reason
        reasons = []
        if moisture < 40:
            reasons.append(f"Low moisture ({moisture:.1f}%)")
        if temperature > 30:
            reasons.append(f"High temperature ({temperature:.1f}°C)")
        if humidity < 40:
            reasons.append(f"Low humidity ({humidity:.1f}%)")
        if rainfall < 2:
            reasons.append(f"No recent rainfall ({rainfall:.1f}mm)")
        
        reason = ", ".join(reasons) if reasons else "Conditions optimal"
        
        return {
            'should_irrigate': should_irrigate,
            'confidence': round(confidence, 3),
            'recommended_amount_mm': round(amount, 2),
            'reason': reason,
            'model_version': 'mock-ml-v1.0',
            'irrigation_score': round(irrigation_score, 3)
        }