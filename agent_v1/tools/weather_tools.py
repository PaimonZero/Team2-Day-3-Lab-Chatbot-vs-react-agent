import requests
from typing import Dict, Any

# ─── WMO Weather Interpretation Codes (ISO 4677) ───────────────────────────────
# Nguồn: https://open-meteo.com/en/docs#weathervariables
WEATHER_CODES: Dict[int, str] = {
    0:  "Trời quang đãng",
    1:  "Chủ yếu quang đãng",
    2:  "Có mây một phần",
    3:  "Nhiều mây / Âm u",
    45: "Có sương mù",
    48: "Sương mù tạo băng",
    51: "Mưa phùn nhẹ",
    53: "Mưa phùn vừa",
    55: "Mưa phùn dày",
    61: "Mưa nhẹ",
    63: "Mưa vừa",
    65: "Mưa to",
    71: "Tuyết rơi nhẹ",
    73: "Tuyết rơi vừa",
    75: "Tuyết rơi dày",
    80: "Mưa rào nhẹ",
    81: "Mưa rào vừa",
    82: "Mưa rào mạnh",
    95: "Dông",
    96: "Dông có mưa đá nhỏ",
    99: "Dông có mưa đá lớn",
}


# ─── Tool Functions ────────────────────────────────────────────────────────────

def get_coordinates(city_name: str) -> str:
    """
    [V1] Lấy vĩ độ (latitude) và kinh độ (longitude) của một thành phố.

    Phiên bản baseline: gọi API một lần, trả về string mô tả rõ ràng.

    Args:
        city_name (str): Tên thành phố cần tra cứu (vd: 'Hanoi', 'Tokyo').

    Returns:
        str: Chuỗi mô tả toạ độ, hoặc thông báo lỗi cụ thể.
    """
    url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={city_name}&count=1&language=en&format=json"
    )

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or len(data["results"]) == 0:
            return (
                f"Lỗi: Không tìm thấy toạ độ cho '{city_name}'. "
                "Hãy kiểm tra lại tên địa danh (nên dùng tiếng Anh, vd: 'Ho Chi Minh City')."
            )

        loc = data["results"][0]
        city    = loc.get("name", city_name)
        country = loc.get("country", "Unknown")
        lat     = loc["latitude"]
        lon     = loc["longitude"]

        return (
            f"Toạ độ của {city} ({country}): "
            f"latitude={lat}, longitude={lon}"
        )

    except requests.exceptions.Timeout:
        return "Lỗi: Yêu cầu tới API geocoding bị timeout. Vui lòng thử lại."
    except requests.exceptions.ConnectionError:
        return "Lỗi: Không thể kết nối API geocoding. Kiểm tra kết nối mạng."
    except Exception as e:
        return f"Lỗi không xác định: {str(e)}"


def get_weather(latitude: float, longitude: float) -> str:
    """
    [V1] Lấy thông tin thời tiết hiện tại từ toạ độ địa lý.

    Trả về: nhiệt độ, tốc độ gió, và mô tả thời tiết (từ weather_code).

    Args:
        latitude  (float): Vĩ độ (vd: 21.0285).
        longitude (float): Kinh độ (vd: 105.8542).

    Returns:
        str: Chuỗi mô tả thời tiết, hoặc thông báo lỗi.
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,wind_speed_10m,weather_code"
    )

    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        current      = data.get("current", {})
        temp         = current.get("temperature_2m", "N/A")
        wind         = current.get("wind_speed_10m", "N/A")
        weather_code = current.get("weather_code")

        # Chuyển mã WMO → mô tả tiếng Việt
        weather_desc = WEATHER_CODES.get(weather_code, f"Trạng thái đặc biệt (mã {weather_code})")

        return (
            f"Thời tiết tại ({latitude}, {longitude}): "
            f"{weather_desc} | Nhiệt độ: {temp}°C | Tốc độ gió: {wind} km/h"
        )

    except requests.exceptions.Timeout:
        return "Lỗi: Yêu cầu thời tiết bị timeout. Vui lòng thử lại."
    except requests.exceptions.ConnectionError:
        return "Lỗi: Không thể kết nối API thời tiết. Kiểm tra kết nối mạng."
    except Exception as e:
        return f"Lỗi lấy dữ liệu thời tiết: {str(e)}"


# ─── Tool Schema – Anthropic Format ───────────────────────────────────────────
WEATHER_TOOLS_CONFIG = [
    {
        "name": "get_coordinates",
        "description": (
            "Lấy vĩ độ (latitude) và kinh độ (longitude) của một địa danh. "
            "PHẢI gọi hàm này TRƯỚC KHI gọi get_weather. "
            "Input: tên thành phố bằng tiếng Anh (vd: 'Tokyo', 'Hanoi'). "
            "Không được tự suy đoán hoặc hardcode toạ độ."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "Tên thành phố hoặc địa danh (vd: 'Tokyo', 'Ho Chi Minh City')"
                }
            },
            "required": ["city_name"]
        }
    },
    {
        "name": "get_weather",
        "description": (
            "Tra cứu thời tiết hiện tại. "
            "Input BẮT BUỘC là latitude và longitude kiểu float, "
            "lấy từ kết quả của tool 'get_coordinates'. "
            "Không được tự đoán hay điền toạ độ ngẫu nhiên."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Vĩ độ kiểu float (vd: 21.0285)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Kinh độ kiểu float (vd: 105.8542)"
                }
            },
            "required": ["latitude", "longitude"]
        }
    }
]

# Dispatcher dùng trong ReAct Agent loop
TOOL_FUNCTIONS = {
    "get_coordinates": get_coordinates,
    "get_weather": get_weather,
}


# ─── Quick Demo ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("[V1] Weather Tools - Quick Test")
    print("=" * 55)

    # Test 1: Lấy toạ độ
    city = "Hanoi"
    result_coords = get_coordinates(city)
    print(f"\n[get_coordinates] '{city}'")
    print(f"  → {result_coords}")

    # Test 2: Lấy thời tiết theo toạ độ Hà Nội
    result_weather = get_weather(21.0285, 105.8542)
    print(f"\n[get_weather] lat=21.0285, lon=105.8542")
    print(f"  → {result_weather}")

    # Test 3: Tên thành phố không tồn tại
    result_err = get_coordinates("XYZ_UnknownCity999")
    print(f"\n[get_coordinates] 'XYZ_UnknownCity999' (test lỗi)")
    print(f"  → {result_err}")
