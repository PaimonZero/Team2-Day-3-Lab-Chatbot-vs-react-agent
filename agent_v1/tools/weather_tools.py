import requests
import json
from typing import Dict, Any

def get_coordinates(city_name: str) -> str:
    """
    [V1] Tìm kiếm kinh độ và vĩ độ của một thành phố.
    Phiên bản cơ bản: Gọi API 1 lần, trả về kết quả đơn giản.
    """
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if "results" not in data or len(data["results"]) == 0:
            return f"Lỗi: Không tìm thấy toạ độ cho thành phố '{city_name}'."
            
        location = data["results"][0]
        return f"Toạ độ của {city_name}: latitude={location['latitude']}, longitude={location['longitude']}"
        
    except Exception as e:
        return f"Lỗi API: {str(e)}"

def get_weather(latitude: float, longitude: float) -> str:
    """
    [V1] Lấy thông tin thời tiết cơ bản dựa trên toạ độ.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m,weather_code"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        temp = current.get("temperature_2m", "Unknown")
        wind = current.get("wind_speed_10m", "Unknown")
        
        return f"Thời tiết tại ({latitude}, {longitude}): Nhiệt độ {temp}°C, Tốc độ gió {wind} km/h."
        
    except Exception as e:
        return f"Lỗi lấy thời tiết: {str(e)}"

# Meta-data Configuration để nhét vào System Prompt của LLM
WEATHER_TOOLS_CONFIG = [
    {
        "name": "get_coordinates",
        "description": "Dùng để lấy vĩ độ (latitude) và kinh độ (longitude) của một địa danh. Input là tên thành phố (vd: 'Tokyo'). Phải gọi hàm này trước khi gọi get_weather.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "Tên phổ thông của thành phố hoặc địa danh"
                }
            },
            "required": ["city_name"]
        }
    },
    {
        "name": "get_weather",
        "description": "Dùng để tra cứu thời tiết hiện tại. Bắt buộc input phải là latitude (toạ độ ngang) và longitude (toạ độ dọc) kiểu số thực (float).",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Vĩ độ (vd: 21.02)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Kinh độ (vd: 105.83)"
                }
            },
            "required": ["latitude", "longitude"]
        }
    }
]
