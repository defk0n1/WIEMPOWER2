import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
from loguru import logger

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

# Now import from src
from src.data_storage import DatabaseManager
from src.npk_analyzer import NPKAnalyzer

# Configure page
st.set_page_config(
    page_title="WIEMPOWER2 - Irrigation Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #2E7D32;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2E7D32;
    }
    .status-good {
        color: #2E7D32;
    }
    .status-warning {
        color: #F57C00;
    }
    .status-critical {
        color: #C62828;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database connection
@st.cache_resource
def get_database():
    db_url = os.getenv('DATABASE_URL', 
        'postgresql://irrigation_user:irrigation_pass@postgres:5432/irrigation_db')
    return DatabaseManager(db_url)

db = get_database()

# Initialize NPK analyzer
@st.cache_resource
def get_npk_analyzer():
    return NPKAnalyzer('../config/npk_config.yaml', db)

npk_analyzer = get_npk_analyzer()

# Header
st.markdown('<h1 class="main-header">🌱 WIEMPOWER2 - Irrigation Monitoring Dashboard</h1>', 
            unsafe_allow_html=True)

# Sidebar
st.sidebar.title("⚙️ Dashboard Controls")
auto_refresh = st.sidebar.checkbox("Auto Refresh (10s)", value=True)
if auto_refresh:
    import time
    time.sleep(10)
    st.rerun()

selected_zone = st.sidebar.selectbox(
    "Select Zone",
    ["All Zones", "zone-1", "zone-2", "zone-3"]
)

time_range = st.sidebar.selectbox(
    "Time Range",
    ["Last Hour", "Last 6 Hours", "Last 24 Hours", "Last 7 Days"],
    index=1
)

# Map time range to hours
time_map = {
    "Last Hour": 1,
    "Last 6 Hours": 6,
    "Last 24 Hours": 24,
    "Last 7 Days": 168
}
hours = time_map[time_range]

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", 
    "🌿 NPK Nutrients", 
    "💧 Water & Moisture", 
    "🌡️ Environment",
    "📈 Analytics"
])

# TAB 1: Overview
with tab1:
    st.header("System Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Get latest readings from database
    session = db.get_session()
    
    try:
        # NPK Status
        with col1:
            from sqlalchemy import func
            from src.data_storage import NPKReading
            
            latest_npk = session.query(NPKReading).order_by(
                NPKReading.timestamp.desc()
            ).first()
            
            if latest_npk:
                st.metric(
                    label="🌿 Latest NPK Reading",
                    value=f"N:{latest_npk.nitrogen:.0f} P:{latest_npk.phosphorus:.0f} K:{latest_npk.potassium:.0f}",
                    delta=f"Zone: {latest_npk.zone_id}"
                )
            else:
                st.metric("🌿 NPK", "No data")
        
        # Water Level
        with col2:
            from src.data_storage import WaterLevelReading
            
            latest_water = session.query(WaterLevelReading).order_by(
                WaterLevelReading.timestamp.desc()
            ).first()
            
            if latest_water:
                st.metric(
                    label="💧 Water Reservoir",
                    value=f"{latest_water.level_percent:.1f}%",
                    delta=f"{latest_water.current_liters:.0f}L / {latest_water.capacity_liters:.0f}L"
                )
            else:
                st.metric("💧 Water", "No data")
        
        # Temperature
        with col3:
            from src.data_storage import SensorReading
            
            latest_temp = session.query(SensorReading).filter(
                SensorReading.sensor_type == 'temperature'
            ).order_by(SensorReading.timestamp.desc()).first()
            
            if latest_temp:
                st.metric(
                    label="🌡️ Temperature",
                    value=f"{latest_temp.value:.1f}°C",
                    delta=f"Zone: {latest_temp.zone_id}"
                )
            else:
                st.metric("🌡️ Temperature", "No data")
        
        # Humidity
        with col4:
            from src.data_storage import HumidityReading
            
            latest_humidity = session.query(HumidityReading).order_by(
                HumidityReading.timestamp.desc()
            ).first()
            
            if latest_humidity:
                st.metric(
                    label="🌫️ Humidity",
                    value=f"{latest_humidity.humidity:.1f}%",
                    delta=f"Zone: {latest_humidity.zone_id}"
                )
            else:
                st.metric("🌫️ Humidity", "No data")
    
    finally:
        session.close()
    
    st.divider()
    
    # Recent Activity
    st.subheader("📋 Recent Activity")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Recent Irrigation Events**")
        session = db.get_session()
        try:
            from src.data_storage import IrrigationEvent
            
            recent_irrigation = session.query(IrrigationEvent).order_by(
                IrrigationEvent.timestamp.desc()
            ).limit(5).all()
            
            if recent_irrigation:
                for event in recent_irrigation:
                    auto_icon = "🤖" if event.automated else "👤"
                    st.markdown(
                        f"{auto_icon} **{event.zone_id}**: {event.amount_mm}mm - "
                        f"_{event.timestamp.strftime('%Y-%m-%d %H:%M')}_"
                    )
            else:
                st.info("No irrigation events yet")
        finally:
            session.close()
    
    with col2:
        st.markdown("**Recent Fertilizer Events**")
        session = db.get_session()
        try:
            from src.data_storage import FertilizerEvent
            
            recent_fertilizer = session.query(FertilizerEvent).order_by(
                FertilizerEvent.timestamp.desc()
            ).limit(5).all()
            
            if recent_fertilizer:
                for event in recent_fertilizer:
                    auto_icon = "🤖" if event.automated else "👤"
                    st.markdown(
                        f"{auto_icon} **{event.zone_id}**: {event.nutrient} {event.amount_kg}kg - "
                        f"_{event.timestamp.strftime('%Y-%m-%d %H:%M')}_"
                    )
            else:
                st.info("No fertilizer events yet")
        finally:
            session.close()

# TAB 2: NPK Nutrients
with tab2:
    st.header("🌿 NPK Nutrient Analysis")
    
    session = db.get_session()
    try:
        from src.data_storage import NPKReading
        
        # Time filter
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = session.query(NPKReading).filter(
            NPKReading.timestamp >= cutoff_time
        )
        
        if selected_zone != "All Zones":
            query = query.filter(NPKReading.zone_id == selected_zone)
        
        npk_data = query.order_by(NPKReading.timestamp.desc()).all()
        
        if npk_data:
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': r.timestamp,
                'zone_id': r.zone_id,
                'nitrogen': r.nitrogen,
                'phosphorus': r.phosphorus,
                'potassium': r.potassium
            } for r in npk_data])
            
            # Latest reading
            latest = npk_data[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Nitrogen (N)",
                    f"{latest.nitrogen:.1f} mg/kg",
                    delta="Optimal: 50-80" if 50 <= latest.nitrogen <= 80 else "Check levels"
                )
            
            with col2:
                st.metric(
                    "Phosphorus (P)",
                    f"{latest.phosphorus:.1f} mg/kg",
                    delta="Optimal: 25-50" if 25 <= latest.phosphorus <= 50 else "Check levels"
                )
            
            with col3:
                st.metric(
                    "Potassium (K)",
                    f"{latest.potassium:.1f} mg/kg",
                    delta="Optimal: 120-180" if 120 <= latest.potassium <= 180 else "Check levels"
                )
            
            st.divider()
            
            # NPK Trends Chart
            st.subheader("NPK Trends Over Time")
            
            fig = go.Figure()
            
            for zone in df['zone_id'].unique():
                zone_data = df[df['zone_id'] == zone]
                
                fig.add_trace(go.Scatter(
                    x=zone_data['timestamp'],
                    y=zone_data['nitrogen'],
                    name=f'{zone} - Nitrogen',
                    mode='lines+markers',
                    line=dict(color='green')
                ))
                
                fig.add_trace(go.Scatter(
                    x=zone_data['timestamp'],
                    y=zone_data['phosphorus'],
                    name=f'{zone} - Phosphorus',
                    mode='lines+markers',
                    line=dict(color='orange')
                ))
                
                fig.add_trace(go.Scatter(
                    x=zone_data['timestamp'],
                    y=zone_data['potassium'],
                    name=f'{zone} - Potassium',
                    mode='lines+markers',
                    line=dict(color='blue')
                ))
            
            fig.update_layout(
                title="NPK Levels Over Time",
                xaxis_title="Time",
                yaxis_title="Concentration (mg/kg)",
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Data table
            st.subheader("NPK Data Table")
            st.dataframe(
                df.sort_values('timestamp', ascending=False),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info(f"No NPK data available for the selected time range ({time_range})")
    
    finally:
        session.close()

# TAB 3: Water & Moisture
with tab3:
    st.header("💧 Water & Moisture Monitoring")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Water Reservoir Level")
        
        session = db.get_session()
        try:
            from src.data_storage import WaterLevelReading
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            water_data = session.query(WaterLevelReading).filter(
                WaterLevelReading.timestamp >= cutoff_time
            ).order_by(WaterLevelReading.timestamp.desc()).all()
            
            if water_data:
                df = pd.DataFrame([{
                    'timestamp': r.timestamp,
                    'level_percent': r.level_percent,
                    'current_liters': r.current_liters,
                    'capacity_liters': r.capacity_liters
                } for r in water_data])
                
                # Gauge chart for current level
                latest = water_data[0]
                
                fig = go.Figure(go.Indicator(
                    mode="gauge+number+delta",
                    value=latest.level_percent,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': "Water Level (%)"},
                    delta={'reference': 50},
                    gauge={
                        'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 20], 'color': "lightcoral"},
                            {'range': [20, 40], 'color': "lightyellow"},
                            {'range': [40, 100], 'color': "lightgreen"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 20
                        }
                    }
                ))
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.metric(
                    "Current Volume",
                    f"{latest.current_liters:.0f} L",
                    f"Capacity: {latest.capacity_liters:.0f} L"
                )
        finally:
            session.close()
    
    with col2:
        st.subheader("Soil Moisture")
        
        session = db.get_session()
        try:
            from src.data_storage import SensorReading
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = session.query(SensorReading).filter(
                SensorReading.sensor_type == 'moisture',
                SensorReading.timestamp >= cutoff_time
            )
            
            if selected_zone != "All Zones":
                query = query.filter(SensorReading.zone_id == selected_zone)
            
            moisture_data = query.order_by(SensorReading.timestamp.desc()).all()
            
            if moisture_data:
                df = pd.DataFrame([{
                    'timestamp': r.timestamp,
                    'zone_id': r.zone_id,
                    'moisture': r.value
                } for r in moisture_data])
                
                # Line chart
                fig = px.line(
                    df,
                    x='timestamp',
                    y='moisture',
                    color='zone_id',
                    title='Soil Moisture Over Time',
                    labels={'moisture': 'Moisture (%)', 'timestamp': 'Time'}
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No moisture data available")
        finally:
            session.close()

# TAB 4: Environment
with tab4:
    st.header("🌡️ Environmental Conditions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Temperature")
        
        session = db.get_session()
        try:
            from src.data_storage import SensorReading
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = session.query(SensorReading).filter(
                SensorReading.sensor_type == 'temperature',
                SensorReading.timestamp >= cutoff_time
            )
            
            if selected_zone != "All Zones":
                query = query.filter(SensorReading.zone_id == selected_zone)
            
            temp_data = query.order_by(SensorReading.timestamp.desc()).all()
            
            if temp_data:
                df = pd.DataFrame([{
                    'timestamp': r.timestamp,
                    'zone_id': r.zone_id,
                    'temperature': r.value
                } for r in temp_data])
                
                fig = px.line(
                    df,
                    x='timestamp',
                    y='temperature',
                    color='zone_id',
                    title='Temperature Over Time',
                    labels={'temperature': 'Temperature (°C)'}
                )
                
                st.plotly_chart(fig, use_container_width=True)
        finally:
            session.close()
    
    with col2:
        st.subheader("Humidity")
        
        session = db.get_session()
        try:
            from src.data_storage import HumidityReading
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = session.query(HumidityReading).filter(
                HumidityReading.timestamp >= cutoff_time
            )
            
            if selected_zone != "All Zones":
                query = query.filter(HumidityReading.zone_id == selected_zone)
            
            humidity_data = query.order_by(HumidityReading.timestamp.desc()).all()
            
            if humidity_data:
                df = pd.DataFrame([{
                    'timestamp': r.timestamp,
                    'zone_id': r.zone_id,
                    'humidity': r.humidity,
                    'temperature': r.temperature,
                    'heat_index': r.heat_index,
                    'dew_point': r.dew_point
                } for r in humidity_data])
                
                fig = px.line(
                    df,
                    x='timestamp',
                    y='humidity',
                    color='zone_id',
                    title='Humidity Over Time',
                    labels={'humidity': 'Humidity (% RH)'}
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show latest metrics
                latest = humidity_data[0]
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Humidity", f"{latest.humidity:.1f}%")
                with col_b:
                    st.metric("Heat Index", f"{latest.heat_index:.1f}°C" if latest.heat_index else "N/A")
                with col_c:
                    st.metric("Dew Point", f"{latest.dew_point:.1f}°C" if latest.dew_point else "N/A")
        finally:
            session.close()

# TAB 5: Analytics
with tab5:
    st.header("📈 Analytics & Insights")
    
    st.subheader("System Statistics")
    
    session = db.get_session()
    try:
        from src.data_storage import SensorReading, NPKReading, HumidityReading, WaterLevelReading
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Count readings
        sensor_count = session.query(SensorReading).filter(
            SensorReading.timestamp >= cutoff_time
        ).count()
        
        npk_count = session.query(NPKReading).filter(
            NPKReading.timestamp >= cutoff_time
        ).count()
        
        humidity_count = session.query(HumidityReading).filter(
            HumidityReading.timestamp >= cutoff_time
        ).count()
        
        water_count = session.query(WaterLevelReading).filter(
            WaterLevelReading.timestamp >= cutoff_time
        ).count()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Sensor Readings", sensor_count)
        with col2:
            st.metric("NPK Readings", npk_count)
        with col3:
            st.metric("Humidity Readings", humidity_count)
        with col4:
            st.metric("Water Level Readings", water_count)
    
    finally:
        session.close()
    
    st.divider()
    
    st.info("More analytics features coming soon!")

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🌱 WIEMPOWER2 - Smart Irrigation Monitoring System</p>
        <p>Last updated: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    unsafe_allow_html=True
)