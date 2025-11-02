"""
Database models and storage management
"""

import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from loguru import logger

Base = declarative_base()


class SensorReading(Base):
    """Sensor reading data model"""
    __tablename__ = 'sensor_readings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    zone_id = Column(String(50), nullable=False, index=True)
    sensor_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    depth_cm = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<SensorReading(zone={self.zone_id}, type={self.sensor_type}, value={self.value})>"


class IrrigationEvent(Base):
    """Irrigation event log"""
    __tablename__ = 'irrigation_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    zone_id = Column(String(50), nullable=False, index=True)
    amount_mm = Column(Float, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    automated = Column(Boolean, default=False)
    reason = Column(String(200), nullable=True)
    
    def __repr__(self):
        return f"<IrrigationEvent(zone={self.zone_id}, amount={self.amount_mm}mm)>"


class SoilAnalysis(Base):
    """Soil water analysis results"""
    __tablename__ = 'soil_analysis'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    zone_id = Column(String(50), nullable=False, index=True)
    paw_percentage = Column(Float, nullable=False)
    irrigation_needed = Column(Boolean, nullable=False)
    predicted_days_to_threshold = Column(Integer, nullable=True)
    field_capacity = Column(Float, nullable=True)
    wilting_point = Column(Float, nullable=True)
    current_moisture = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<SoilAnalysis(zone={self.zone_id}, PAW={self.paw_percentage}%)>"


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url=None):
        if database_url is None:
            database_url = os.getenv(
                'DATABASE_URL',
                'postgresql://irrigation_user:irrigation_pass@postgres:5432/irrigation_db'
            )
        
        self.engine = create_engine(database_url, echo=False)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"🗄️  Database connected: {database_url.split('@')[1]}")
    
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(self.engine)
        logger.info("✅ Database tables created")
    
    def get_session(self):
        """Get new database session"""
        return self.Session()
    
    def store_sensor_reading(self, timestamp, zone_id, sensor_type, value, unit, depth_cm=None):
        """Store sensor reading"""
        session = self.get_session()
        try:
            reading = SensorReading(
                timestamp=timestamp,
                zone_id=zone_id,
                sensor_type=sensor_type,
                value=value,
                unit=unit,
                depth_cm=depth_cm
            )
            session.add(reading)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing sensor reading: {e}")
        finally:
            session.close()
    
    def store_irrigation_event(self, timestamp, zone_id, amount_mm, automated=False, reason=None):
        """Store irrigation event"""
        session = self.get_session()
        try:
            event = IrrigationEvent(
                timestamp=timestamp,
                zone_id=zone_id,
                amount_mm=amount_mm,
                automated=automated,
                reason=reason
            )
            session.add(event)
            session.commit()
            logger.info(f"💧 Irrigation event logged: {zone_id}, {amount_mm}mm")
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing irrigation event: {e}")
        finally:
            session.close()
    
    def store_soil_analysis(self, timestamp, zone_id, paw_percentage, 
                           irrigation_needed, current_moisture, 
                           field_capacity=None, wilting_point=None):
        """Store soil analysis result"""
        session = self.get_session()
        try:
            analysis = SoilAnalysis(
                timestamp=timestamp,
                zone_id=zone_id,
                paw_percentage=paw_percentage,
                irrigation_needed=irrigation_needed,
                current_moisture=current_moisture,
                field_capacity=field_capacity,
                wilting_point=wilting_point
            )
            session.add(analysis)

            print("analysis stored")
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing soil analysis: {e}")
        finally:
            session.close()
    def store_npk_reading(self, timestamp, zone_id, nitrogen, phosphorus, potassium, depth_cm=None):
        """Store NPK sensor reading"""
        session = self.get_session()
        try:
            reading = NPKReading(
                timestamp=timestamp,
                zone_id=zone_id,
                nitrogen=nitrogen,
                phosphorus=phosphorus,
                potassium=potassium,
                depth_cm=depth_cm
            )
            session.add(reading)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing NPK reading: {e}")
        finally:
            session.close()

    def store_water_level(self, timestamp, current_liters, capacity_liters, level_percent):
        session = self.get_session()
        try:
            reading = WaterLevelReading(
                timestamp=timestamp,
                current_liters=current_liters,
                capacity_liters=capacity_liters,
                level_percent=level_percent
            )
            session.add(reading)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing water level: {e}")
        finally:
            session.close()

    def store_fertilizer_event(self, timestamp, zone_id, nutrient, amount_kg, automated=False, reason=None):
        session = self.get_session()
        try:
            event = FertilizerEvent(
                timestamp=timestamp,
                zone_id=zone_id,
                nutrient=nutrient,
                amount_kg=amount_kg,
                automated=automated,
                reason=reason
            )
            session.add(event)
            session.commit()
            logger.info(f"🌿 Fertilizer event logged: {zone_id}, {amount_kg}kg {nutrient}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing fertilizer event: {e}")
        finally:
            session.close()
    def store_humidity_reading(self, timestamp, zone_id, humidity, temperature=None, 
                          heat_index=None, dew_point=None):
        session = self.get_session()
        try:
            reading = HumidityReading(
                timestamp=timestamp,
                zone_id=zone_id,
                humidity=humidity,
                temperature=temperature,
                heat_index=heat_index,
                dew_point=dew_point
            )
            session.add(reading)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing humidity reading: {e}")
        finally:
            session.close()


class NPKReading(Base):
    """NPK nutrient sensor readings"""
    __tablename__ = 'npk_readings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    zone_id = Column(String(50), nullable=False, index=True)
    nitrogen = Column(Float, nullable=True)       # mg/kg
    phosphorus = Column(Float, nullable=True)     # mg/kg
    potassium = Column(Float, nullable=True)      # mg/kg
    depth_cm = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<NPKReading(zone={self.zone_id}, N={self.nitrogen}, P={self.phosphorus}, K={self.potassium})>"


class WaterLevelReading(Base):
    """Water reservoir level readings"""
    __tablename__ = 'water_level_readings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    current_liters = Column(Float, nullable=False)
    capacity_liters = Column(Float, nullable=False)
    level_percent = Column(Float, nullable=False)
    
    def __repr__(self):
        return f"<WaterLevelReading(level={self.level_percent}%, {self.current_liters}L)>"


class FertilizerEvent(Base):
    """Fertilizer application log"""
    __tablename__ = 'fertilizer_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    zone_id = Column(String(50), nullable=False, index=True)
    nutrient = Column(String(10), nullable=False)  # 'N', 'P', or 'K'
    amount_kg = Column(Float, nullable=False)
    automated = Column(Boolean, default=False)
    reason = Column(String(200), nullable=True)
    
    def __repr__(self):
        return f"<FertilizerEvent(zone={self.zone_id}, nutrient={self.nutrient}, amount={self.amount_kg}kg)>"
    


class HumidityReading(Base):
    """Air humidity sensor readings"""
    __tablename__ = 'humidity_readings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    zone_id = Column(String(50), nullable=False, index=True)
    humidity = Column(Float, nullable=False)          # % RH
    temperature = Column(Float, nullable=True)         # °C (DHT22 reads both)
    heat_index = Column(Float, nullable=True)          # °C
    dew_point = Column(Float, nullable=True)           # °C
    
    def __repr__(self):
        return f"<HumidityReading(zone={self.zone_id}, humidity={self.humidity}% RH)>"