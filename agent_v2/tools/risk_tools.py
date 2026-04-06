"""
AGENT V2 — Risk & Escalation Tools (Improved)
===============================================
NGƯỜI LÀM: Đặng Tùng Anh - 2A202600026
Cải tiến từ V1:
- 4 cấp độ rủi ro: LOW / MEDIUM / HIGH / CRITICAL
- Thêm comfort_index (chỉ số cảm giác nhiệt)
- Escalation có incident_id chuyên nghiệp hơn
- Error handling rõ ràng hơn
- Tích hợp src.telemetry.logger
"""

import sys
import os
import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.telemetry.logger import logger


def analyze_risk(temperature_c, wind_speed_kmh, weather_code):
    """
    Phân tích rủi ro chi tiết với 4 cấp độ.

    Args:
        temperature_c: Nhiệt độ (°C)
        wind_speed_kmh: Tốc độ gió (km/h)
        weather_code: Mã thời tiết WMO

    Returns:
        dict với: risk_level, comfort_index, reasons, recommendation, status
    """
    advice = []
    reasons = []
    risk_level = "LOW"
    comfort_index = "THOẢI MÁI"

    # Validate đầu vào
    try:
        weather_code = int(weather_code)
    except (TypeError, ValueError):
        return {
            "risk_level": "UNKNOWN",
            "comfort_index": "N/A",
            "reasons": ["Lỗi: Dữ liệu thời tiết không hợp lệ (weather_code)."],
            "recommendation": "Không thể phân tích rủi ro do dữ liệu đầu vào không hợp lệ.",
            "status": "ERROR"
        }

    # 1. Phân loại rủi ro chi tiết (4 cấp độ) dựa trên Gió và Bão
    if wind_speed_kmh > 100 or weather_code in [96, 99]:
        risk_level = "CRITICAL"
        reasons.append(f"Siêu bão/Sét đánh mạnh (wind: {wind_speed_kmh} km/h, code: {weather_code})")
        advice.append("CẢNH BÁO NGUY HIỂM: SIÊU BÃO/SÉT ĐÁNH MẠNH. KHÔNG RA NGOÀI.")
    elif wind_speed_kmh > 60 or weather_code == 95:
        risk_level = "HIGH"
        reasons.append(f"Gió mạnh/Bão (wind: {wind_speed_kmh} km/h, code: {weather_code})")
        advice.append("CẢNH BÁO: Gió mạnh/Bão. Hạn chế tối đa việc di chuyển.")
    elif wind_speed_kmh > 30:
        risk_level = "MEDIUM"
        reasons.append(f"Gió hơi mạnh ({wind_speed_kmh} km/h)")
        advice.append("Gió hơi mạnh, cần chú ý khi mang theo ô.")

    # 2. Kiểm tra Nhiệt độ & Comfort Index
    if temperature_c > 30:
        comfort_index = "NÓNG"
        reasons.append(f"Nhiệt độ cao ({temperature_c}°C)")
        if weather_code <= 2:
            advice.append("Trời nắng nóng gay gắt, hãy mang theo kem chống nắng và kính râm.")
        else:
            advice.append("Trời khá nóng, bạn nên chú ý uống nhiều nước.")
    elif temperature_c < 10:
        comfort_index = "RẤT LẠNH"
        reasons.append(f"Nhiệt độ rất thấp ({temperature_c}°C)")
        advice.append("Cần mang áo ấm siêu dày và giữ nhiệt.")
    elif 10 <= temperature_c < 20:
        comfort_index = "SE LẠNH"
        reasons.append(f"Nhiệt độ se lạnh ({temperature_c}°C)")
        advice.append("Trời se lạnh, một chiếc áo khoác là cần thiết.")

    # 3. Kiểm tra Mưa
    if (51 <= weather_code <= 67) or (80 <= weather_code <= 82):
        reasons.append(f"Có mưa (weather_code: {weather_code})")
        advice.append("Có mưa. Lời khuyên: Mang theo dù (ô) hoặc áo mưa.")

    recommendation = " ".join(advice) if advice else "Thời tiết lý tưởng cho các hoạt động ngoài trời. ✅"
    if not reasons:
        reasons = ["Không có yếu tố rủi ro đáng kể."]

    logger.log_event("RISK_ANALYSIS_V2", {
        "risk_level": risk_level,
        "comfort_index": comfort_index,
        "temperature_c": temperature_c,
        "wind_speed_kmh": wind_speed_kmh,
        "weather_code": weather_code,
    })

    return {
        "risk_level": risk_level,
        "comfort_index": comfort_index,
        "reasons": reasons,
        "recommendation": recommendation,
        "status": "PROCESSED_V2"
    }


def escalate_to_human(reason, city):
    """
    Thông báo leo thang chuyên nghiệp (Professional Escalation).

    Args:
        reason: Lý do escalation
        city: Thành phố liên quan

    Returns:
        dict với: status, message, incident_id
    """
    incident_id = f"INC-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    logger.log_event("ESCALATION_V2", {
        "incident_id": incident_id,
        "city": city,
        "reason": reason,
    })

    return {
        "status": "escalated",
        "incident_id": incident_id,
        "message": (
            f"[HỆ THỐNG CẢNH BÁO V2]: Sự cố mã {incident_id} tại {city} đã được ghi nhận. "
            f"Lý do: {reason}. "
            "Đã chuyển tiếp thông tin khẩn cấp đến đội cứu trợ du lịch địa phương."
        ),
    }
