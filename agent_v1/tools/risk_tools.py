"""
AGENT V1 — Risk & Escalation Tools
=====================================
NGƯỜI LÀM: Đặng Tùng Anh - 2A202600026

Implement 2 functions:
- analyze_risk(temperature_c, wind_speed_kmh, weather_code) → risk level + khuyến nghị
- escalate_to_human(reason, city) → simulate notify travel agent

V1: Rule-based đơn giản, 2 mức rủi ro LOW/HIGH.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.telemetry.logger import logger


def analyze_risk(temperature_c, wind_speed_kmh, weather_code):
    """
    Phân tích rủi ro cơ bản dựa trên luật (Rule-based).

    Args:
        temperature_c: Nhiệt độ (°C)
        wind_speed_kmh: Tốc độ gió (km/h)
        weather_code: Mã thời tiết WMO

    Returns:
        dict với: risk_level, reasons, recommendation
    """
    advice = []
    reasons = []
    risk_level = "LOW"

    # Validate đầu vào
    try:
        weather_code = int(weather_code)
    except (TypeError, ValueError):
        return {
            "risk_level": "UNKNOWN",
            "reasons": ["Lỗi: Dữ liệu thời tiết không hợp lệ (weather_code)."],
            "recommendation": "Không thể phân tích rủi ro do dữ liệu đầu vào không hợp lệ."
        }

    # 1. Kiểm tra Bão (wind_speed hoặc weather_code 95-99)
    if wind_speed_kmh > 60 or weather_code in [95, 96, 99]:
        risk_level = "HIGH"
        reasons.append(f"Gió mạnh/Bão nguy hiểm (wind: {wind_speed_kmh} km/h, code: {weather_code})")
        advice.append("CẢNH BÁO: Gió mạnh/Bão nguy hiểm. Hạn chế ra ngoài.")

    # 2. Kiểm tra Mưa (weather_code 51-82)
    if (51 <= weather_code <= 67) or (80 <= weather_code <= 82):
        reasons.append(f"Có mưa (weather_code: {weather_code})")
        advice.append("Có mưa, hãy mang theo dù (ô).")

    # 3. Kiểm tra Nhiệt độ
    if temperature_c < 15:
        reasons.append(f"Nhiệt độ thấp ({temperature_c}°C)")
        advice.append("Trời lạnh, hãy chuẩn bị áo ấm dày.")
    elif temperature_c < 22:
        reasons.append(f"Nhiệt độ hơi lạnh ({temperature_c}°C)")
        advice.append("Trời hơi se lạnh, nên mang áo khoác nhẹ.")
    elif temperature_c > 30:
        reasons.append(f"Nhiệt độ cao ({temperature_c}°C)")
        if weather_code <= 2:
            advice.append("Trời nắng nóng gay gắt, hãy mặc chống nắng hoặc kính râm.")
        else:
            advice.append("Trời khá nóng, bạn nên chú ý uống nhiều nước.")

    recommendation = " ".join(advice) if advice else "Thời tiết ổn định, không có lưu ý đặc biệt. ✅"
    if not reasons:
        reasons = ["Không có yếu tố rủi ro đáng kể."]

    logger.log_event("RISK_ANALYSIS_V1", {
        "risk_level": risk_level,
        "temperature_c": temperature_c,
        "wind_speed_kmh": wind_speed_kmh,
        "weather_code": weather_code,
    })

    return {
        "risk_level": risk_level,
        "reasons": reasons,
        "recommendation": recommendation,
    }


def escalate_to_human(reason, city):
    """
    Giả lập việc thông báo cho nhân viên hỗ trợ (Escalation).

    Args:
        reason: Lý do escalation
        city: Thành phố liên quan

    Returns:
        dict với: status, message, ticket_id
    """
    import random
    ticket_id = f"ESC-{random.randint(1000, 9999)}"

    log_message = f"[ESCALATION V1] Đã thông báo cho đại lý du lịch về sự cố tại {city}. Lý do: {reason}"
    logger.log_event("ESCALATION_V1", {"city": city, "reason": reason, "ticket_id": ticket_id})

    return {
        "status": "escalated",
        "message": f"Đã kết nối với bộ phận hỗ trợ khách hàng để xử lý tại {city}.",
        "ticket_id": ticket_id,
    }
