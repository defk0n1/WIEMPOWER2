from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime
import os
import uvicorn

# ============================================================================
# CONFIGURATION
# ============================================================================

app = FastAPI(title="Irrigation Scheduler API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "meta-llama/llama-3.1-8b-instruct"

# Weather API
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"

# Fixed configuration (no user input needed)
LATITUDE = 36.8065
LONGITUDE = 10.1815
CURRENT_SOIL_MOISTURE = 70.0
SOIL_MOISTURE_THRESHOLD = 62.5
DAYS = 7

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fetch_weather():
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "windspeed_10m_max",
            "relative_humidity_2m_mean",
            "et0_fao_evapotranspiration",
            "weathercode"
        ],
        "timezone": "auto",
        "forecast_days": DAYS
    }
    
    response = requests.get(OPEN_METEO_API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    weather_data = []
    daily = data['daily']
    
    weather_codes = {
        0: "Clear", 1: "Clear", 2: "Partly Cloudy", 3: "Cloudy",
        45: "Foggy", 48: "Foggy", 51: "Drizzle", 53: "Drizzle",
        55: "Drizzle", 61: "Rain", 63: "Rain", 65: "Rain",
        71: "Snow", 73: "Snow", 75: "Snow", 80: "Rain Showers",
        81: "Rain Showers", 82: "Rain Showers", 95: "Thunderstorm"
    }
    
    for i in range(len(daily['time'])):
        weather_data.append({
            "date": daily['time'][i],
            "temp_max": daily['temperature_2m_max'][i],
            "temp_min": daily['temperature_2m_min'][i],
            "precipitation": daily['precipitation_sum'][i],
            "precipitation_probability": daily['precipitation_probability_max'][i],
            "humidity": daily['relative_humidity_2m_mean'][i],
            "wind_speed": daily['windspeed_10m_max'][i],
            "evapotranspiration": daily['et0_fao_evapotranspiration'][i],
            "conditions": weather_codes.get(daily['weathercode'][i], "Unknown")
        })
    
    return weather_data


def simulate_soil_moisture():
    moisture_readings = []
    moisture = CURRENT_SOIL_MOISTURE
    
    for day in range(DAYS):
        daily_loss = 3 + (day * 0.5)
        moisture = max(25.0, moisture - daily_loss)
        moisture_readings.append(round(moisture, 1))
    
    return moisture_readings


def create_prompt(weather_data, soil_moisture_data):
    weather_summary = ""
    for i, day in enumerate(weather_data):
        weather_summary += f"\nDay {i+1} ({day['date']}):\n"
        weather_summary += f"  - Temperature: {day['temp_min']}°C to {day['temp_max']}°C\n"
        weather_summary += f"  - Conditions: {day['conditions']}\n"
        weather_summary += f"  - Precipitation: {day['precipitation']} mm (probability: {day['precipitation_probability']}%)\n"
        weather_summary += f"  - Humidity: {day['humidity']}%\n"
        weather_summary += f"  - Wind Speed: {day['wind_speed']} m/s\n"
        weather_summary += f"  - Evapotranspiration: {day['evapotranspiration']} mm\n"
        weather_summary += f"  - Projected Soil Moisture: {soil_moisture_data[i]}%\n"
    
    prompt = f"""You are an agricultural irrigation advisor. Based on weather forecasts and soil moisture data, decide the irrigation schedule for the next 7 days.

IRRIGATION RULES:
- Soil Moisture Threshold: {SOIL_MOISTURE_THRESHOLD}%
- Current Soil Moisture: {CURRENT_SOIL_MOISTURE}%

DECISION GUIDELINES:
1. If soil moisture < {SOIL_MOISTURE_THRESHOLD}%, irrigation is needed
2. If rain > 10mm is forecasted with >70% probability, skip irrigation
3. High evapotranspiration (>5mm) increases water need

WEATHER FORECAST & SOIL MOISTURE:
{weather_summary}

TASK: For each day, decide: IRRIGATE, SKIP, or MONITOR.

Format your response EXACTLY as:
DAY 1: [DECISION] - [reason]
DAY 2: [DECISION] - [reason]
DAY 3: [DECISION] - [reason]
DAY 4: [DECISION] - [reason]
DAY 5: [DECISION] - [reason]
DAY 6: [DECISION] - [reason]
DAY 7: [DECISION] - [reason]
"""
    return prompt


def call_llm(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1000
    }
    
    response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']


def parse_llm_response(llm_output):
    lines = llm_output.strip().split('\n')
    schedule = []
    
    for line in lines:
        if line.startswith('DAY'):
            parts = line.split(':')
            if len(parts) >= 2:
                decision_part = parts[1].strip()
                
                if 'IRRIGATE' in decision_part.upper():
                    decision = 'IRRIGATE'
                elif 'SKIP' in decision_part.upper():
                    decision = 'SKIP'
                elif 'MONITOR' in decision_part.upper():
                    decision = 'MONITOR'
                else:
                    decision = 'UNKNOWN'
                
                schedule.append(decision)
    
    return schedule

# ============================================================================
# SINGLE ENDPOINT
# ============================================================================

@app.post("/schedule")
async def get_schedule():
    """
    Generate irrigation schedule - returns JSON with dates and decisions
    No input needed, uses weather API automatically
    """
    try:
        # Fetch weather
        weather_data = fetch_weather()
        
        # Simulate soil moisture
        soil_moisture_data = simulate_soil_moisture()
        
        # Create prompt and call LLM
        prompt = create_prompt(weather_data, soil_moisture_data)
        llm_response = call_llm(prompt)
        
        # Parse decisions
        decisions = parse_llm_response(llm_response)
        
        # Format output
        result = []
        for i in range(min(len(weather_data), len(decisions))):
            result.append({
                "date": weather_data[i]['date'],
                "decision": decisions[i]
            })
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting Irrigation Scheduler API on http://localhost:5002")
    print("📍 Endpoint: POST http://localhost:5002/schedule")
    print("📚 Docs: http://localhost:5002/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=5002)