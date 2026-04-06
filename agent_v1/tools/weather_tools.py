"""
AGENT V1 — Weather Tools
=========================
NGƯỜI LÀM: Thành viên A

Implement 2 functions:
- get_coordinates(city: str) → gọi Open-Meteo Geocoding API
- get_weather(lat: float, lon: float) → gọi Open-Meteo Forecast API

Lưu ý V1: Không có retry, không validate đầu vào, basic error handling.
"""

import requests
from typing import Optional

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL  = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes (simplified)
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


def get_coordinates(city: str) -> dict:
    """
    Lấy tọa độ (lat, lon) của một thành phố.

    Args:
        city: Tên thành phố (ví dụ: "Hanoi", "Tokyo")

    Returns:
        dict với keys: lat, lon, name, country
        Hoặc dict với key 'error' nếu không tìm thấy
    """
    params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format": "json"
    }

    response = requests.get(GEOCODING_URL, params=params, timeout=10)
    data = response.json()

    if not data.get("results"):
        return {"error": f"City '{city}' not found"}

    result = data["results"][0]
    return {
        "lat": result["latitude"],
        "lon": result["longitude"],
        "name": result["name"],
        "country": result.get("country", "Unknown"),
    }


def get_weather(lat: float, lon: float) -> dict:
    """
    Lấy thông tin thời tiết hiện tại theo tọa độ.

    Args:
        lat: Vĩ độ
        lon: Kinh độ

    Returns:
        dict với: temperature_c, wind_speed_kmh, weather_code, weather_desc
        Hoặc dict với key 'error' nếu API lỗi
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "wind_speed_10m",
            "weather_code",
        ],
        "wind_speed_unit": "kmh",
        "forecast_days": 1,
    }

    response = requests.get(FORECAST_URL, params=params, timeout=10)
    data = response.json()

    if "current" not in data:
        return {"error": "Failed to fetch weather data"}

    current = data["current"]
    weather_code = current.get("weather_code", 0)

    return {
        "temperature_c": current.get("temperature_2m"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "weather_code": weather_code,
        "weather_desc": WMO_CODES.get(weather_code, f"Unknown code {weather_code}"),
    }
