"""Weather plugin - English, uses Open-Meteo (no API key)"""

import requests

DEFAULT_LAT = 23.8103
DEFAULT_LON = 90.4125
DEFAULT_CITY = "Dhaka"


def _weather_desc(code):
    mapping = {
        0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
        45: "foggy", 48: "depositing rime fog",
        51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
        61: "slight rain", 63: "moderate rain", 65: "heavy rain",
        71: "slight snow", 73: "moderate snow", 75: "heavy snow",
        80: "rain showers", 81: "moderate rain showers", 82: "violent rain showers",
        95: "thunderstorm", 96: "thunderstorm with hail", 99: "heavy thunderstorm",
    }
    return mapping.get(code, "unknown")


def get_weather(city: str = None) -> str:
    try:
        city_name = city or DEFAULT_CITY
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={DEFAULT_LAT}&longitude={DEFAULT_LON}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            f"&timezone=auto"
        )
        r = requests.get(url, timeout=10)
        data = r.json()
        cur = data.get("current", {})
        temp = round(cur.get("temperature_2m", 0))
        humidity = cur.get("relative_humidity_2m", 0)
        code = cur.get("weather_code", 0)
        wind = round(cur.get("wind_speed_10m", 0))

        return (
            f"It's {temp} degrees in {city_name} right now, with {_weather_desc(code)}. "
            f"Humidity is {humidity} percent and wind speed is {wind} kilometers per hour. "
            f"Have a wonderful day!"
        )
    except Exception as e:
        return f"Sorry, I can't fetch the weather right now. ({e})"