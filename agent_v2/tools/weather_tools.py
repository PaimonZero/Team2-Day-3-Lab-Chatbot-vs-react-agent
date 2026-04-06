import json
import logging
import time
from typing import Any, Dict, Optional

import requests

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("weather_tools_v2")

# ─── WMO Weather Interpretation Codes ─────────────────────────────────────────
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


# ─── Internal Helpers ──────────────────────────────────────────────────────────

def _get_with_retry(
    url: str,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
) -> Dict[str, Any]:
    """
    Gọi HTTP GET với retry và exponential backoff.

    Chiến lược:
      - Lần 1: thử ngay
      - Lần 2: đợi backoff_factor^0 = 1.5s
      - Lần 3: đợi backoff_factor^1 = 2.25s
      - Sau max_retries lần → raise exception cuối cùng

    Args:
        url           (str)  : URL cần gọi.
        max_retries   (int)  : Số lần thử tối đa (default=3).
        backoff_factor(float): Hệ số tính thời gian chờ giữa các lần retry.

    Raises:
        requests.exceptions.RequestException: Khi hết lượt retry.
    """
    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.debug("Attempt %d/%d → GET %s", attempt, max_retries, url)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < max_retries:
                wait = backoff_factor ** (attempt - 1)
                logger.warning(
                    "Lần thử %d/%d thất bại (%s). Retry sau %.1fs…",
                    attempt, max_retries, exc, wait,
                )
                time.sleep(wait)
            else:
                logger.error(
                    "Tất cả %d lần thử đều thất bại. Lỗi cuối: %s",
                    max_retries, exc,
                )

    raise last_error  # type: ignore[misc]


def _describe_weather(code: Optional[int]) -> str:
    """Dịch mã WMO weather_code → mô tả tiếng Việt."""
    if code is None:
        return "Không xác định"
    return WEATHER_CODES.get(code, f"Trạng thái đặc biệt (mã {code})")


def _error_json(code: str, message: str) -> str:
    """Tạo JSON error response chuẩn."""
    return json.dumps(
        {"status": "error", "error_code": code, "message": message},
        ensure_ascii=False,
    )


# ─── Public Tool Functions ─────────────────────────────────────────────────────

def get_coordinates(city_name: str) -> str:
    """
    [V2] Lấy toạ độ địa lý (latitude, longitude) của một thành phố.

    Cải tiến so với V1:
      - Retry 3 lần với exponential backoff
      - Trả về JSON chuẩn {status, city, country, latitude, longitude}
      - Error JSON có error_code để Agent tự xử lý fallback

    Args:
        city_name (str): Tên thành phố (vd: 'Hanoi', 'Ho Chi Minh City').

    Returns:
        str: JSON string với status="success" hoặc status="error".
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
    [V2] Lấy thông tin thời tiết hiện tại đầy đủ từ toạ độ.

    Cải tiến so với V1:
      - Thêm: feels_like, humidity, precipitation, rain, wind_gusts, visibility
      - weather_description tiếng Việt từ WMO weather_code
      - Trả về JSON chuẩn → Risk Engine dễ phân tích
      - Retry 3 lần với backoff; visibility xử lý graceful khi null

    Args:
        latitude  (float): Vĩ độ (vd: 21.0285).
        longitude (float): Kinh độ (vd: 105.8542).

    Returns:
        str: JSON string chứa đầy đủ thông tin thời tiết.
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

        # visibility có thể None ở một số khu vực → giữ nguyên None, không crash
        obs: Dict[str, Any] = {
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
            # None nếu API không hỗ trợ khu vực này; Risk Engine cần kiểm tra null
            "visibility_m": current.get("visibility"),
        }
        return json.dumps(obs, ensure_ascii=False)

    except requests.exceptions.Timeout:
        return _error_json("TIMEOUT", "API thời tiết không phản hồi (timeout). Hãy thử lại.")
    except requests.exceptions.ConnectionError:
        return _error_json("CONNECTION_ERROR", "Không thể kết nối API thời tiết. Kiểm tra kết nối mạng.")
    except Exception as exc:
        return _error_json("UNKNOWN", f"Lỗi không xác định khi lấy thời tiết: {exc}")


# ─── Tool Schema – Anthropic Format ───────────────────────────────────────────
WEATHER_TOOLS_CONFIG = [
    {
        "name": "get_coordinates",
        "description": (
            "LẤY TOẠ ĐỘ ĐỊA LÝ. "
            "Bạn PHẢI gọi tool này ĐẦU TIÊN bất cứ khi nào người dùng đề cập đến tên địa điểm "
            "mà bạn chưa có latitude/longitude xác thực. "
            "KHÔNG được tự suy đoán toạ độ từ kiến thức của bạn — dữ liệu PHẢI đến từ tool này. "
            "Trả về JSON: {status, city, country, latitude, longitude}."
        ),
        "input_schema": {
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
            "tốc độ gió, gió giật, tầm nhìn, mô tả thời tiết tiếng Việt. "
            "Dùng dữ liệu này để Risk Engine phân tích và đưa ra khuyến nghị an toàn."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Vĩ độ kiểu Float, lấy từ kết quả của get_coordinates.",
                },
                "longitude": {
                    "type": "number",
                    "description": "Kinh độ kiểu Float, lấy từ kết quả của get_coordinates.",
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


# ─── Quick Demo / Test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("🌦️   [V2] Weather Tools – Full Test Suite")
    print("=" * 60)

    # ── Test 1: Happy path – Hà Nội ──────────────────────────────
    print("\n[TEST 1] get_coordinates('Hanoi')")
    raw = get_coordinates("Hanoi")
    coords = json.loads(raw)
    print(json.dumps(coords, indent=2, ensure_ascii=False))

    if coords["status"] == "success":
        lat, lon = coords["latitude"], coords["longitude"]
        print(f"\n[TEST 2] get_weather(lat={lat}, lon={lon})")
        raw_wx = get_weather(lat, lon)
        weather = json.loads(raw_wx)
        print(json.dumps(weather, indent=2, ensure_ascii=False))

    # ── Test 2: Thành phố không tồn tại ─────────────────────────
    print("\n[TEST 3] get_coordinates('XYZ_UnknownCity123')  ← error case")
    raw_err = get_coordinates("XYZ_UnknownCity123")
    print(json.dumps(json.loads(raw_err), indent=2, ensure_ascii=False))

    # ── Test 3: Thêm một thành phố khác ─────────────────────────
    print("\n[TEST 4] get_coordinates('Da Nang')")
    raw_dn = get_coordinates("Da Nang")
    coords_dn = json.loads(raw_dn)
    print(json.dumps(coords_dn, indent=2, ensure_ascii=False))