import requests


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather_data(latitude, longitude):
    """
    Fetch current environmental data from Open-Meteo.
    """

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "rain",
            "soil_temperature_0cm",
            "soil_moisture_0_to_1cm",
            "et0_fao_evapotranspiration",
            "vapour_pressure_deficit"
        ]),

        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "rain",
            "wind_speed_10m",
            "soil_temperature_0_to_7cm",
            "soil_moisture_0_to_7cm",
            "et0_fao_evapotranspiration",
            "vapour_pressure_deficit"
        ]),

        "forecast_days": 7,
        "timezone": "auto"
    }

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        current = data.get("current", {})
        units = data.get("current_units", {})

        result = {
            "location": {
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone")
            },

            "current": {
                "temperature": current.get("temperature_2m"),
                "temperature_unit": units.get("temperature_2m"),

                "humidity": current.get("relative_humidity_2m"),
                "humidity_unit": units.get("relative_humidity_2m"),

                "wind_speed": current.get("wind_speed_10m"),
                "wind_speed_unit": units.get("wind_speed_10m"),

                "rain": current.get("rain"),
                "rain_unit": units.get("rain"),

                "soil_temperature": current.get(
                    "soil_temperature_0cm"
                ),
                "soil_temperature_unit": units.get(
                    "soil_temperature_0cm"
                ),

                "soil_moisture": current.get(
                    "soil_moisture_0_to_1cm"
                ),
                "soil_moisture_unit": units.get(
                    "soil_moisture_0_to_1cm"
                ),

                "et0": current.get(
                    "et0_fao_evapotranspiration"
                ),
                "et0_unit": units.get(
                    "et0_fao_evapotranspiration"
                ),

                "vpd": current.get(
                    "vapour_pressure_deficit"
                ),
                "vpd_unit": units.get(
                    "vapour_pressure_deficit"
                )
            },

            "hourly": data.get("hourly", {}),
            "hourly_units": data.get("hourly_units", {})
        }

        return result

    except requests.exceptions.RequestException as e:
        print(f"Open-Meteo API Error: {e}")
        return None

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return None


def print_weather(data):
    """
    Display Open-Meteo data in terminal.
    """

    if not data:
        print("\n❌ Weather data unavailable.")
        return

    location = data["location"]
    current = data["current"]

    print("\n" + "=" * 55)
    print("🌦️ AGROVISION - OPEN-METEO ENVIRONMENT DATA")
    print("=" * 55)

    print(f"\n📍 Latitude       : {location['latitude']}")
    print(f"📍 Longitude      : {location['longitude']}")
    print(f"🕐 Timezone       : {location['timezone']}")

    print("\n🌡️ CURRENT CONDITIONS")
    print("-" * 55)

    print(
        f"Temperature      : "
        f"{current['temperature']} "
        f"{current['temperature_unit']}"
    )

    print(
        f"Humidity         : "
        f"{current['humidity']} "
        f"{current['humidity_unit']}"
    )

    print(
        f"Wind Speed       : "
        f"{current['wind_speed']} "
        f"{current['wind_speed_unit']}"
    )

    print(
        f"Rain             : "
        f"{current['rain']} "
        f"{current['rain_unit']}"
    )

    print(
        f"Soil Temperature : "
        f"{current['soil_temperature']} "
        f"{current['soil_temperature_unit']}"
    )

    print(
        f"Soil Moisture    : "
        f"{current['soil_moisture']} "
        f"{current['soil_moisture_unit']}"
    )

    print(
        f"ET₀              : "
        f"{current['et0']} "
        f"{current['et0_unit']}"
    )

    print(
        f"VPD              : "
        f"{current['vpd']} "
        f"{current['vpd_unit']}"
    )

    print("\n" + "=" * 55)
    print("✅ Open-Meteo data received successfully")
    print("=" * 55)


if __name__ == "__main__":

    print("\n🌱 AGROVISION")
    print("Open-Meteo Environment API Test")
    print("-" * 55)

    try:
        latitude = float(
            input("Enter Latitude: ").strip()
        )

        longitude = float(
            input("Enter Longitude: ").strip()
        )

    except ValueError:
        print("\n❌ Invalid latitude or longitude.")
        print("Example: 22.7196")
        exit()

    print("\n⏳ Fetching live environment data...")

    weather_data = get_weather_data(
        latitude,
        longitude
    )

    print_weather(weather_data)