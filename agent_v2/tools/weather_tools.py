import requests
import json
import time
from typing import Dict, Any

def _get_with_retry(url: str, max_retries: int = 2) -> Dict[str, Any]:
    """Helper gọi API có cơ chế retry."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1) # Đợi 1 giây rồi thử lại

def get_coordinates(city_name: str) -> str:
    """
    [V2 - Improved] Lấy tọa độ với cơ chế Fallback và Error Handling tốt hơn,
    cung cấp output cho Agent dưới dạng JSON String chuẩn xác để dễ parse.
    """
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1&language=en&format=json"
    
    try:
        data = _get_with_retry(url)
        
        if "results" not in data or len(data["results"]) == 0:
            return json.dumps({
                "status": "error",
                "message": f"Không tìm thấy thành phố có tên '{city_name}'. Vui lòng yêu cầu người dùng xác nhận lại tên địa danh."
            }, ensure_ascii=False)
            
        location = data["results"][0]
        return json.dumps({
            "status": "success",
            "city": location.get('name'),
            "country": location.get('country', 'Unknown'),
            "latitude": location['latitude'],
            "longitude": location['longitude']
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"API Geocoding gặp sự cố: {str(e)}"}, ensure_ascii=False)

def get_weather(latitude: float, longitude: float) -> str:
    """
    [V2 - Improved] Lấy thời tiết mở rộng (thêm độ ẩm, lượng mưa, tầm nhìn)
    để hỗ trợ Risk Engine đánh giá chính xác độ an toàn.
    """
    # Thêm tham số: relative_humidity_2m, precipitation, visibility
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m,visibility"
    
    try:
        data = _get_with_retry(url)
        current = data.get("current", {})
        
        # Trả về Observation là một block thông tin chuẩn chỉnh
        obs_data = {
            "status": "success",
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "precipitation_mm": current.get("precipitation"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "visibility_m": current.get("visibility")
        }
        return json.dumps(obs_data, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Lỗi lấy dữ liệu thời tiết thực tế: {str(e)}"}, ensure_ascii=False)

# V2: Viết prompt (description) cho Tool khắt khe hơn, giúp AI ko bị Hallucination
WEATHER_TOOLS_CONFIG = [
    {
        "name": "get_coordinates",
        "description": "LẤY TOẠ ĐỘ. Bạn LUÔN PHẢI gọi tool này ĐẦU TIÊN khi user nhắc đến tên một địa điểm mà bạn chưa biết kinh độ/vĩ độ. Trả về JSON chứa latitude, longitude.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "Tên thành phố (Ví dụ: 'Tokyo', 'Hanoi'). Không bao gồm các từ ngữ thừa."
                }
            },
            "required": ["city_name"]
        }
    },
    {
        "name": "get_weather",
        "description": "LẤY THỜI TIẾT THỰC TẾ. Mệnh lệnh: Không được tự đoán thời tiết. Bắt buộc input parameter phải là 'latitude' và 'longitude' kiểu float, lấy được từ tool 'get_coordinates'. Cung cấp chi tiết nhiết độ, sức gió, mưa, tầm nhìn.",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Vĩ độ kiểu Float."
                },
                "longitude": {
                    "type": "number",
                    "description": "Kinh độ kiểu Float."
                }
            },
            "required": ["latitude", "longitude"]
        }
    }
]
