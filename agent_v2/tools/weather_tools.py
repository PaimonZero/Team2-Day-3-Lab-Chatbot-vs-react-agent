import json
import time
from typing import Any, Dict, Optional

import requests

# ─── WMO Weather Interpretation Codes → Tiếng Việt ───────────────────────────
WEATHER_CODES: Dict[int, str] = {
    0:  "Trời quang đãng ☀️",
    1:  "Chủ yếu quang đãng 🌤️",
    2:  "Có mây một phần ⛅",
    3:  "Nhiều mây / Âm u ☁️",
    45: "Có sương mù 🌫️",
    48: "Sương mù tạo băng 🌫️❄️",
    51: "Mưa phùn nhẹ 🌦️",
    53: "Mưa phùn vừa 🌦️",
    55: "Mưa phùn dày 🌧️",
    61: "Mưa nhẹ 🌧️",
    63: "Mưa vừa 🌧️",
    65: "Mưa to 🌧️",
    71: "Tuyết rơi nhẹ 🌨️",
    73: "Tuyết rơi vừa 🌨️",
    75: "Tuyết rơi dày ❄️",
    80: "Mưa rào nhẹ 🌦️",
    81: "Mưa rào vừa 🌧️",
    82: "Mưa rào mạnh ⛈️",
    95: "Dông ⛈️",
    96: "Dông có mưa đá nhỏ ⛈️🌨️",
    99: "Dông có mưa đá lớn ⛈️❄️",
}


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _get_with_retry(
    url: str,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
) -> Dict[str, Any]:
    """
    Gọi HTTP GET với exponential backoff retry.

    Chiến lược:
      - Lần 1: thử ngay
      - Lần 2: đợi backoff_factor^0 = 1.5s
      - Lần 3: đợi backoff_factor^1 = 2.25s
      - Sau max_retries lần → raise exception cuối cùng

    Raises:
        requests.exceptions.RequestException: khi hết lượt retry.
    """
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < max_retries:
                wait = backoff_factor ** (attempt - 1)
                time.sleep(wait)

    raise last_error  # type: ignore[misc]


def _describe_weather(code: Optional[int]) -> str:
    """Dịch mã WMO weather_code → mô tả tiếng Việt."""
    if code is None:
        return "Không xác định"
    return WEATHER_CODES.get(code, f"Trạng thái đặc biệt (mã {code})")


def _error_json(code: str, message: str) -> str:
    """Tạo JSON error response chuẩn có error_code để Agent tự xử lý."""
    return json.dumps(
        {"status": "error", "error_code": code, "message": message},
        ensure_ascii=False,
    )


# ─── Public Tool Functions ────────────────────────────────────────────────────

def get_coordinates(city_name: str) -> str:
    """
    Lấy toạ độ địa lý (latitude, longitude) của một thành phố.

    Args:
        city_name (str): Tên thành phố (vd: 'Hanoi', 'Ho Chi Minh City').

    Returns:
        str: JSON string với status="success" hoặc status="error".
             Success: {status, city, country, latitude, longitude}
             Error:   {status, error_code, message}
    """
    url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={city_name}&count=1&language=en&format=json"
    )

    try:
        data = _get_with_retry(url)

        if "results" not in data or len(data["results"]) == 0:
            return _error_json(
                "CITY_NOT_FOUND",
                (
                    f"Không tìm thấy thành phố '{city_name}'. "
                    "Hãy hỏi người dùng xác nhận tên địa danh, "
                    "hoặc thử tên tiếng Anh (vd: 'Ho Chi Minh City' thay vì 'TP HCM')."
                ),
            )

        loc = data["results"][0]
        return json.dumps(
            {
                "status": "success",
                "city": loc.get("name"),
                "country": loc.get("country", "Unknown"),
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
            },
            ensure_ascii=False,
        )

    except requests.exceptions.Timeout:
        return _error_json("TIMEOUT", "API geocoding không phản hồi (timeout). Hãy thử lại sau vài giây.")
    except requests.exceptions.ConnectionError:
        return _error_json("CONNECTION_ERROR", "Không thể kết nối API geocoding. Kiểm tra kết nối mạng.")
    except Exception as exc:
        return _error_json("UNKNOWN", f"Lỗi không xác định khi tìm toạ độ: {exc}")


def get_weather(latitude: float, longitude: float) -> str:
    """
    Lấy thông tin thời tiết hiện tại đầy đủ từ toạ độ.

    Args:
        latitude  (float): Vĩ độ — lấy từ kết quả get_coordinates.
        longitude (float): Kinh độ — lấy từ kết quả get_coordinates.

    Returns:
        str: JSON string chứa đầy đủ thông tin thời tiết.
             Success: {status, weather_description, weather_code,
                       temperature_c, feels_like_c, humidity_percent,
                       precipitation_mm, rain_mm, wind_speed_kmh,
                       wind_gusts_kmh, visibility_m}
             Error:   {status, error_code, message}
    """
    params = ",".join([
        "temperature_2m",
        "apparent_temperature",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "weather_code",
        "wind_speed_10m",
        "wind_gusts_10m",
        "visibility",
    ])
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}&current={params}"
    )

    try:
        data = _get_with_retry(url)
        current = data.get("current", {})
        weather_code = current.get("weather_code")

        return json.dumps(
            {
                "status": "success",
                "weather_description": _describe_weather(weather_code),
                "weather_code": weather_code,
                "temperature_c": current.get("temperature_2m"),
                "feels_like_c": current.get("apparent_temperature"),
                "humidity_percent": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation", 0.0),
                "rain_mm": current.get("rain", 0.0),
                "wind_speed_kmh": current.get("wind_speed_10m"),
                "wind_gusts_kmh": current.get("wind_gusts_10m"),
                # None nếu API không hỗ trợ khu vực này
                "visibility_m": current.get("visibility"),
            },
            ensure_ascii=False,
        )

    except requests.exceptions.Timeout:
        return _error_json("TIMEOUT", "API thời tiết không phản hồi (timeout). Hãy thử lại.")
    except requests.exceptions.ConnectionError:
        return _error_json("CONNECTION_ERROR", "Không thể kết nối API thời tiết. Kiểm tra kết nối mạng.")
    except Exception as exc:
        return _error_json("UNKNOWN", f"Lỗi không xác định khi lấy thời tiết: {exc}")


# ─── Tool Schema – dùng trong agent nếu cần ──────────────────────────────────
WEATHER_TOOLS_CONFIG = [
    {
        "name": "get_coordinates",
        "description": (
            "LẤY TOẠ ĐỘ ĐỊA LÝ. "
            "Bạn PHẢI gọi tool này ĐẦU TIÊN bất cứ khi nào user đề cập đến tên địa điểm "
            "mà bạn chưa có latitude/longitude xác thực. "
            "KHÔNG được tự suy đoán toạ độ — dữ liệu PHẢI đến từ tool này. "
            "Trả về JSON: {status, city, country, latitude, longitude}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": (
                        "Tên thành phố bằng tiếng Anh hoặc tên quốc tế phổ thông "
                        "(vd: 'Hanoi', 'Ho Chi Minh City', 'Da Nang', 'Tokyo'). "
                        "Không thêm từ phụ như 'thành phố', 'tỉnh', 'quận'."
                    ),
                }
            },
            "required": ["city_name"],
        },
    },
    {
        "name": "get_weather",
        "description": (
            "LẤY THỜI TIẾT THỰC TẾ. "
            "LUÔN PHẢI gọi 'get_coordinates' TRƯỚC để lấy toạ độ chính xác. "
            "TUYỆT ĐỐI không được tự đoán hay hardcode latitude/longitude. "
            "Trả về JSON đầy đủ: nhiệt độ, cảm giác nhiệt, độ ẩm, lượng mưa, "
            "tốc độ gió, gió giật, tầm nhìn, mô tả thời tiết tiếng Việt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Vĩ độ kiểu Float — lấy từ kết quả của get_coordinates.",
                },
                "longitude": {
                    "type": "number",
                    "description": "Kinh độ kiểu Float — lấy từ kết quả của get_coordinates.",
                },
            },
            "required": ["latitude", "longitude"],
        },
    },
]

# Dispatcher dùng trong ReAct Agent loop
TOOL_FUNCTIONS = {
    "get_coordinates": get_coordinates,
    "get_weather": get_weather,
}
