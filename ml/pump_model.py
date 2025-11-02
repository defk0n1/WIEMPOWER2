"""
XGBoost-based ML Model Service for Irrigation Pump Decisions
Flask API that predicts whether water pump should be activated
"""

from flask import Flask, request, jsonify
from datetime import datetime
import numpy as np
import logging
import os
import joblib

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# Model configuration
MODEL_VERSION = "v1.0.0-xgboost"
MODEL_TYPE = "xgboost"
MODEL_PATH = os.getenv('MODEL_PATH', 'xgb_pump_model.pkl')


class XGBoostPumpModel:
    """
    XGBoost Model for Water Pump Activation
    Predicts whether irrigation pump should be activated based on environmental factors
    """
    
    def __init__(self, model_path: str):
        """
        Initialize XGBoost Model
        
        Args:
            model_path: Path to the trained XGBoost model (.pkl file)
        """
        self.model_path = model_path
        self.model = None
        self.version = MODEL_VERSION
        self.model_type = MODEL_TYPE
        
        # Feature order (must match training data)
        self.feature_names = [
            'Temperature',      # Air/Soil temperature in Celsius
            'Humidity',         # Air humidity percentage
            'water_level',      # Soil moisture/water level percentage
            'N',                # Nitrogen (mg/kg)
            'P',                # Phosphorus (mg/kg)
            'K'                 # Potassium (mg/kg)
        ]
        
        self.load_model()
    
    def load_model(self):
        """Load the trained XGBoost model"""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found: {self.model_path}")
            
            self.model = joblib.load(self.model_path)
            logger.info(f"✅ XGBoost model loaded successfully from {self.model_path}")
            logger.info(f"   Model type: {type(self.model)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
    
    def predict(self, features: dict) -> dict:
        """
        Predict irrigation pump activation
        
        Args:
            features: Dictionary containing sensor readings
                - temperature_celsius: float (air or soil temperature)
                - humidity_percent: float (0-100)
                - moisture_percent or water_level: float (0-100)
                - nitrogen_mgkg: float
                - phosphorus_mgkg: float
                - potassium_mgkg: float
                
        Returns:
            Dictionary with prediction results
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Extract and prepare features
        try:
            # Map input features to model expected format
            temperature = features.get('temperature_celsius', features.get('Temperature', 25.0))
            humidity = features.get('humidity_percent', features.get('Humidity', 60.0))
            
            # Water level can come as moisture_percent or water_level
            water_level = features.get('water_level', 
                         features.get('moisture_percent', 
                         features.get('water_level_percent', 50.0)))
            
            nitrogen = features.get('nitrogen_mgkg', features.get('N', 50.0))
            phosphorus = features.get('phosphorus_mgkg', features.get('P', 30.0))
            potassium = features.get('potassium_mgkg', features.get('K', 150.0))
            
            # Prepare input array (order must match training data)
            input_array = np.array([[
                temperature,
                humidity,
                water_level,
                nitrogen,
                phosphorus,
                potassium
            ]])
            
            logger.debug(f"Input features: Temperature={temperature}, Humidity={humidity}, "
                        f"WaterLevel={water_level}, N={nitrogen}, P={phosphorus}, K={potassium}")
            
            # Get prediction probability
            prob_array = self.model.predict_proba(input_array)
            probability = float(prob_array[0][1])  # Probability of class 1 (activate pump)
            
            # Make binary decision (threshold = 0.5)
            should_irrigate = bool(probability > 0.5)
            
            # Calculate confidence (distance from decision boundary)
            confidence = abs(probability - 0.5) * 2  # Scale 0.5-1.0 to 0-1.0
            
            # Calculate recommended amount based on probability and moisture deficit
            recommended_amount = self._calculate_amount(
                probability, water_level, temperature, humidity
            )
            
            # Generate reason
            reason = self._generate_reason(
                should_irrigate, probability, water_level, temperature, 
                humidity, nitrogen, phosphorus, potassium
            )
            
            # Prepare response
            prediction = {
                'should_irrigate': should_irrigate,
                'confidence': round(float(confidence), 3),
                'probability': round(probability, 3),
                'recommended_amount_mm': round(recommended_amount, 2),
                'reason': reason,
                'model_version': self.version,
                'model_type': self.model_type,
                'features_used': {
                    'temperature': temperature,
                    'humidity': humidity,
                    'water_level': water_level,
                    'nitrogen': nitrogen,
                    'phosphorus': phosphorus,
                    'potassium': potassium
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"🔮 XGBoost Prediction: irrigate={should_irrigate}, "
                       f"probability={probability:.3f}, amount={recommended_amount}mm")
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Prediction error: {e}")
            raise
    
    def _calculate_amount(self, probability: float, water_level: float, 
                         temperature: float, humidity: float) -> float:
        """
        Calculate recommended irrigation amount based on prediction probability
        
        Args:
            probability: Model prediction probability (0-1)
            water_level: Current water/moisture level (0-100)
            temperature: Temperature in Celsius
            humidity: Humidity percentage
            
        Returns:
            Recommended amount in mm
        """
        if probability <= 0.5:
            return 0.0
        
        # Base amount scaled by probability
        base_amount = 15.0
        prob_factor = (probability - 0.5) * 2  # Scale 0.5-1.0 to 0-1.0
        
        # Adjust for water deficit
        optimal_water_level = 60.0
        deficit = max(0, optimal_water_level - water_level)
        deficit_factor = deficit / 40  # Normalize
        
        # Adjust for environmental conditions
        temp_factor = 1.0 + max(0, (temperature - 25) / 20)
        humidity_factor = 1.0 + max(0, (60 - humidity) / 60)
        
        # Calculate final amount
        amount = base_amount * prob_factor * (1 + deficit_factor) * temp_factor * humidity_factor
        
        # Cap at reasonable limits
        amount = max(5.0, min(amount, 25.0))
        
        return amount
    
    def _generate_reason(self, should_irrigate: bool, probability: float,
                        water_level: float, temperature: float, humidity: float,
                        nitrogen: float, phosphorus: float, potassium: float) -> str:
        """Generate human-readable explanation for the decision"""
        
        if should_irrigate:
            reasons = []
            
            if water_level < 40:
                reasons.append(f"Low water level ({water_level:.1f}%)")
            
            if temperature > 30:
                reasons.append(f"High temperature ({temperature:.1f}°C)")
            
            if humidity < 40:
                reasons.append(f"Low humidity ({humidity:.1f}%)")
            
            if nitrogen < 40 or phosphorus < 25 or potassium < 100:
                reasons.append("Nutrient levels suboptimal")
            
            if reasons:
                return f"XGBoost model recommends irrigation (p={probability:.3f}): {', '.join(reasons)}"
            else:
                return f"XGBoost model recommends preventive irrigation (p={probability:.3f})"
        else:
            if water_level > 60:
                return f"Adequate water level ({water_level:.1f}%) - No irrigation needed (p={probability:.3f})"
            else:
                return f"Current conditions adequate - No irrigation needed (p={probability:.3f})"


# Initialize model
try:
    model = XGBoostPumpModel(MODEL_PATH)
    logger.info(f"🤖 XGBoost Pump Model Service initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize model: {e}")
    model = None


# API Routes
@app.route('/predict', methods=['POST'])
def predict():
    """
    Main prediction endpoint
    
    Request Body (Option 1 - Direct format):
    {
        "Temperature": 28.3,
        "Humidity": 55.2,
        "water_level": 35.5,
        "N": 45.0,
        "P": 30.0,
        "K": 150.0
    }
    
    Request Body (Option 2 - Irrigation system format):
    {
        "temperature_celsius": 28.3,
        "humidity_percent": 55.2,
        "moisture_percent": 35.5,
        "nitrogen_mgkg": 45.0,
        "phosphorus_mgkg": 30.0,
        "potassium_mgkg": 150.0,
        "zone_id": "zone-1"
    }
    
    Response:
    {
        "should_irrigate": true,
        "confidence": 0.854,
        "probability": 0.927,
        "recommended_amount_mm": 12.5,
        "reason": "XGBoost model recommends irrigation...",
        "model_version": "v1.0.0-xgboost",
        "model_type": "xgboost",
        ...
    }
    """
    if model is None:
        return jsonify({
            'error': 'Model not loaded',
            'status': 'error'
        }), 500
    
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'No JSON data provided',
                'status': 'error'
            }), 400
        
        logger.info(f"📥 Prediction request received: zone={data.get('zone_id', 'unknown')}")
        logger.debug(f"   Features: {data}")
        
        # Make prediction
        prediction = model.predict(data)
        
        # Add request metadata
        prediction['request'] = {
            'zone_id': data.get('zone_id'),
            'received_at': datetime.utcnow().isoformat()
        }

        print(jsonify(prediction))
        
        return jsonify(prediction), 200
        
    except Exception as e:
        logger.error(f"❌ Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    model_loaded = model is not None and model.model is not None
    
    return jsonify({
        'status': 'healthy' if model_loaded else 'degraded',
        'service': 'irrigation-xgboost-model',
        'version': MODEL_VERSION,
        'model_type': MODEL_TYPE,
        'model_loaded': model_loaded,
        'timestamp': datetime.utcnow().isoformat()
    }), 200 if model_loaded else 503


@app.route('/info', methods=['GET'])
def info():
    """Model information endpoint"""
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    return jsonify({
        'model_version': model.version,
        'model_type': model.model_type,
        'model_path': model.model_path,
        'features': model.feature_names,
        'feature_order': 'Temperature, Humidity, water_level, N, P, K',
        'endpoints': {
            '/predict': 'POST - Make irrigation prediction',
            '/health': 'GET - Health check',
            '/info': 'GET - Model information',
            '/test': 'GET - Test prediction with sample data'
        }
    }), 200


@app.route('/test', methods=['GET'])
def test():
    """Test endpoint with sample data"""
    if model is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    sample_data = {
        'Temperature': 28.3,
        'Humidity': 55.2,
        'water_level': 35.5,
        'N': 45.0,
        'P': 30.0,
        'K': 150.0,
        'zone_id': 'test-zone'
    }
    
    prediction = model.predict(sample_data)
    
    return jsonify({
        'message': 'Test prediction with sample data',
        'sample_input': sample_data,
        'prediction': prediction
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    model_status = 'loaded' if (model and model.model) else 'not loaded'
    
    return jsonify({
        'service': 'XGBoost Irrigation Pump Model Service',
        'version': MODEL_VERSION,
        'status': 'running',
        'model_status': model_status,
        'documentation': '/info'
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info("="*60)
    logger.info("🤖 Starting XGBoost Irrigation Pump Model Service")
    logger.info(f"   Version: {MODEL_VERSION}")
    logger.info(f"   Model Path: {MODEL_PATH}")
    logger.info(f"   Port: {port}")
    logger.info("="*60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)