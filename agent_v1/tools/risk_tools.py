"""
AGENT V1 — Risk Tools
======================
NGƯỜI LÀM: Thành viên B

Implement 2 functions:
- analyze_risk(temperature_c, wind_speed_kmh, weather_code) → risk level + khuyến nghị
- escalate_to_human(reason: str, city: str) → simulate notify travel agent

Lưu ý V1: Risk levels đơn giản (LOW / HIGH), chưa có MEDIUM/CRITICAL.
"""

from typing import Optional

# WMO codes được coi là nguy hiểm
DANGEROUS_WEATHER_CODES = {80, 81, 82, 95, 96, 99}  # showers + thunderstorms
SNOWY_WEATHER_CODES     = {71, 73, 75}               # snow


def analyze_risk(
    temperature_c: float,
    wind_speed_kmh: float,
    weather_code: int,
) -> dict:
    """
    Phân tích mức độ rủi ro khi đi du lịch dựa trên điều kiện thời tiết.

    Args:
        temperature_c: Nhiệt độ (°C)
        wind_speed_kmh: Tốc độ gió (km/h)
        weather_code: Mã thời tiết WMO

    Returns:
        dict với: risk_level, reasons (list), recommendation
    """
    reasons = []

    # --- Nhiệt độ ---
    if temperature_c >= 38:
        reasons.append(f"Extreme heat ({temperature_c}°C) — risk of heat stroke")
    elif temperature_c <= 0:
        reasons.append(f"Freezing temperature ({temperature_c}°C) — roads may be icy")
    elif temperature_c >= 35:
        reasons.append(f"Very hot ({temperature_c}°C) — stay hydrated")

    # --- Gió ---
    if wind_speed_kmh >= 60:
        reasons.append(f"Strong wind ({wind_speed_kmh} km/h) — dangerous for outdoor activities")
    elif wind_speed_kmh >= 40:
        reasons.append(f"Moderate wind ({wind_speed_kmh} km/h) — be cautious")

    # --- Mã thời tiết ---
    if weather_code in DANGEROUS_WEATHER_CODES:
        reasons.append(f"Dangerous weather condition (code {weather_code}: storms/heavy showers)")
    elif weather_code in SNOWY_WEATHER_CODES:
        reasons.append(f"Snow detected (code {weather_code}) — travel may be disrupted")

    # --- Kết luận risk level ---
    if len(reasons) >= 2 or weather_code in DANGEROUS_WEATHER_CODES:
        risk_level = "HIGH"
        recommendation = "⛔ Not recommended to travel. Consider postponing your trip."
    elif len(reasons) == 1:
        risk_level = "MEDIUM"
        recommendation = "⚠️ Travel with caution. Check updates before departing."
    else:
        risk_level = "LOW"
        recommendation = "✅ Conditions look good. Enjoy your trip!"

    return {
        "risk_level": risk_level,
        "reasons": reasons if reasons else ["No significant risk factors detected"],
        "recommendation": recommendation,
    }


def escalate_to_human(reason: str, city: str) -> dict:
    """
    Simulate việc thông báo cho travel agent khi rủi ro quá cao.

    Args:
        reason: Lý do escalation
        city: Thành phố liên quan

    Returns:
        dict với: status, message, ticket_id (giả lập)
    """
    import random
    ticket_id = f"ESC-{random.randint(1000, 9999)}"

    print(f"\n🚨 [ESCALATION] Notifying travel agent...")
    print(f"   City   : {city}")
    print(f"   Reason : {reason}")
    print(f"   Ticket : {ticket_id}")

    return {
        "status": "escalated",
        "message": f"Travel agent has been notified about '{reason}' for {city}.",
        "ticket_id": ticket_id,
    }
