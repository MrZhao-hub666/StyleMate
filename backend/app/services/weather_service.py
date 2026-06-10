"""
天气服务 — wttr.in API
"""

import httpx


async def get_current_weather(city: str = "北京") -> dict:
    """
    获取当前天气

    Args:
        city: 城市名，中文或英文均可

    Returns:
        {"city": "北京", "temp": 22, "condition": "晴", "humidity": 55, "wind": "15km/h"}
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://wttr.in/{city}",
                params={"format": "j1", "lang": "zh"},
            )
            resp.raise_for_status()
            data = resp.json()

            current = data["current_condition"][0]
            condition = current["lang_zh"][0]["value"] if current.get("lang_zh") else current["weatherDesc"][0]["value"]
            # 兜底翻译英文→中文
            EN_MAP = {"Sunny": "晴", "Clear": "晴", "Partly cloudy": "多云", "Cloudy": "阴", "Overcast": "阴",
                      "Rain": "雨", "Light rain": "小雨", "Moderate rain": "中雨", "Heavy rain": "大雨",
                      "Snow": "雪", "Fog": "雾", "Mist": "薄雾", "Haze": "霾"}
            condition = EN_MAP.get(condition, condition)
            return {
                "city": city,
                "temp": int(current["temp_C"]),
                "condition": condition,
                "humidity": int(current["humidity"]),
                "wind": current["winddir16Point"] + " " + current["windspeedKmph"] + "km/h",
                "feels_like": int(current["FeelsLikeC"]),
            }
    except Exception:
        return {
            "city": city,
            "temp": 22,
            "condition": "晴",
            "humidity": 55,
            "wind": "2级",
            "tip": "离线模式，使用默认数据",
        }
