import requests
from typing import Optional, Dict

# 说明: 该模块负责城市地理编码与实时天气查询，使用 Open-Meteo 免费 API。
# 关键流程：
# 1) 通过地理编码 API 将城市名称转换为纬度/经度
# 2) 调用天气 API 获取当前温度与天气代码
# 3) 将天气代码映射为中文描述并返回结构化结果


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo 天气代码到中文描述的简单映射
WEATHER_CODE_MAP = {
    0: "晴空",
    1: "多云少",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "霜雾",
    51: "毛毛雨：弱",
    53: "毛毛雨：中",
    55: "毛毛雨：强",
    56: "冻毛毛雨：弱",
    57: "冻毛毛雨：强",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨：弱",
    67: "冻雨：强",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "冰粒",
    80: "阵雨：弱",
    81: "阵雨：中",
    82: "阵雨：强",
    85: "阵雪：弱",
    86: "阵雪：强",
    95: "雷暴",
    96: "雷暴伴轻微冰雹",
    99: "雷暴伴强烈冰雹",
}


def geocode_city(name: str, language: str = "zh", count: int = 1) -> Optional[Dict]:
    """根据城市名进行地理编码，返回最匹配的地点信息。

    :param name: 城市名称（例如：北京、上海、深圳）
    :param language: 返回语言（默认中文）
    :param count: 返回候选数量（默认只取第一条）
    :return: 地点字典（包含 latitude/longitude/name/country 等）或 None
    """
    try:
        params = {"name": name, "count": count, "language": language, "format": "json"}
        resp = requests.get(GEOCODE_URL, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        if not results:
            return None
        return results[0]
    except Exception:
        return None


def fetch_current_weather(latitude: float, longitude: float, timezone: str = "auto") -> Optional[Dict]:
    """获取指定坐标的当前天气信息。

    :param latitude: 纬度
    :param longitude: 经度
    :param timezone: 时区（默认自动）
    :return: 包含 temperature_2m、weather_code、time 的字典或 None
    """
    try:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code",
            "timezone": timezone,
        }
        resp = requests.get(FORECAST_URL, params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        return data.get("current")
    except Exception:
        return None


def code_to_description(code: Optional[int]) -> str:
    """将天气代码转换为中文描述。"""
    if code is None:
        return "未知"
    return WEATHER_CODE_MAP.get(code, f"未知天气({code})")


def get_city_weather(city_name: str, language: str = "zh") -> Optional[Dict]:
    """综合查询：从城市名称到当前天气的完整流程。

    返回示例：
    {
        "city": "北京",
        "country": "中国",
        "latitude": 39.9,
        "longitude": 116.4,
        "temperature_c": 2.3,
        "description": "多云",
        "observed_at": "2025-12-22T10:00"
    }
    """
    place = geocode_city(city_name, language=language)
    if not place:
        return None
    lat = place.get("latitude")
    lon = place.get("longitude")
    current = fetch_current_weather(lat, lon)
    if not current:
        return None
    temp = current.get("temperature_2m")
    code = current.get("weather_code")
    desc = code_to_description(code)
    observed_time = current.get("time")
    return {
        "city": place.get("name") or city_name,
        "country": place.get("country"),
        "latitude": lat,
        "longitude": lon,
        "temperature_c": temp,
        "description": desc,
        "observed_at": observed_time,
    }

