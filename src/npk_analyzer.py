
import yaml
from datetime import datetime, timezone, timedelta
from loguru import logger


class NPKAnalyzer:
    """Analyze NPK nutrient levels and recommend fertilization"""
    
    def __init__(self, config_path='config/npk_config.yaml', db_manager=None):
        self.db = db_manager
        self.load_config(config_path)
        logger.info("🌿 NPK Analyzer initialized")
    
    def load_config(self, config_path):
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info("✅ NPK configuration loaded")
        except Exception as e:
            logger.error(f"Failed to load NPK config: {e}")
            # Default fallback
            self.config = {
                'npk_thresholds': {
                    'nitrogen': {'critical_low': 20, 'low': 40, 'optimal_min': 60, 'optimal_max': 120},
                    'phosphorus': {'critical_low': 10, 'low': 20, 'optimal_min': 30, 'optimal_max': 60},
                    'potassium': {'critical_low': 50, 'low': 100, 'optimal_min': 150, 'optimal_max': 300}
                }
            }
    
    def analyze_nutrient(self, nutrient_name, value):
        thresholds = self.config['npk_thresholds'].get(nutrient_name.lower(), {})
        
        status = 'UNKNOWN'
        if value < thresholds.get('critical_low', 0):
            status = 'CRITICAL'
        elif value < thresholds.get('low', 0):
            status = 'LOW'
        elif value < thresholds.get('optimal_min', 0):
            status = 'DEFICIENT'
        elif value <= thresholds.get('optimal_max', 999):
            status = 'OPTIMAL'
        else:
            status = 'EXCESS'
        
        return {
            'nutrient': nutrient_name.upper(),
            'value': value,
            'status': status,
            'thresholds': thresholds
        }
    
    def analyze_npk(self, zone_id, nitrogen, phosphorus, potassium, crop_type='wheat'):
        
        # Analyze each nutrient
        n_analysis = self.analyze_nutrient('nitrogen', nitrogen)
        p_analysis = self.analyze_nutrient('phosphorus', phosphorus)
        k_analysis = self.analyze_nutrient('potassium', potassium)
        
        # Get crop requirements
        crop_req = self.config.get('crop_requirements', {}).get(crop_type, {})
        
        # Determine fertilization needs
        fertilization_needed = False
        recommendations = []
        
        # Nitrogen
        if n_analysis['status'] in ['CRITICAL', 'LOW', 'DEFICIENT']:
            n_deficit = crop_req.get('N', {}).get('min', 80) - nitrogen
            if n_deficit > 0:
                n_amount = (n_deficit / 20) * self.config['fertilizer_application']['N_deficit_rate_kg_per_ha']
                recommendations.append({
                    'nutrient': 'N',
                    'amount_kg_per_ha': round(n_amount, 1),
                    'reason': f'Nitrogen deficit: {n_deficit:.1f} mg/kg below optimal'
                })
                fertilization_needed = True
        
        # Phosphorus
        if p_analysis['status'] in ['CRITICAL', 'LOW', 'DEFICIENT']:
            p_deficit = crop_req.get('P', {}).get('min', 30) - phosphorus
            if p_deficit > 0:
                p_amount = (p_deficit / 10) * self.config['fertilizer_application']['P_deficit_rate_kg_per_ha']
                recommendations.append({
                    'nutrient': 'P',
                    'amount_kg_per_ha': round(p_amount, 1),
                    'reason': f'Phosphorus deficit: {p_deficit:.1f} mg/kg below optimal'
                })
                fertilization_needed = True
        
        # Potassium
        if k_analysis['status'] in ['CRITICAL', 'LOW', 'DEFICIENT']:
            k_deficit = crop_req.get('K', {}).get('min', 150) - potassium
            if k_deficit > 0:
                k_amount = (k_deficit / 50) * self.config['fertilizer_application']['K_deficit_rate_kg_per_ha']
                recommendations.append({
                    'nutrient': 'K',
                    'amount_kg_per_ha': round(k_amount, 1),
                    'reason': f'Potassium deficit: {k_deficit:.1f} mg/kg below optimal'
                })
                fertilization_needed = True
        
        return {
            'zone_id': zone_id,
            'crop_type': crop_type,
            'nitrogen': n_analysis,
            'phosphorus': p_analysis,
            'potassium': k_analysis,
            'fertilization_needed': fertilization_needed,
            'recommendations': recommendations,
            'overall_status': self._get_overall_status([n_analysis, p_analysis, k_analysis])
        }
    
    def _get_overall_status(self, analyses):
        statuses = [a['status'] for a in analyses]
        
        if 'CRITICAL' in statuses:
            return 'CRITICAL'
        elif 'LOW' in statuses or 'DEFICIENT' in statuses:
            return 'DEFICIENT'
        elif 'EXCESS' in statuses:
            return 'EXCESS'
        else:
            return 'OPTIMAL'
