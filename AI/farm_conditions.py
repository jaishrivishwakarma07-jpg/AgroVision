
import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def get_location(city):
    """Find the latitude and longitude of a farm location."""

    try:
        response = requests.get(
            GEOCODING_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json"
            },
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        locations = data.get("results", [])

        if not locations:
            print("\nLocation not found. Please check the city name.")
            return None

        return locations[0]

    except requests.RequestException as error:
        print(f"\nLocation API error: {error}")
        return None


def get_farm_conditions(latitude, longitude):
    """Fetch current weather and environmental conditions."""

    try:
        response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "precipitation,"
                    "rain,"
                    "wind_speed_10m,"
                    "wind_direction_10m"
                ),
                "hourly": (
                    "soil_temperature_0cm,"
                    "soil_moisture_0_to_1cm"
                ),
                "forecast_days": 1,
                "timezone": "auto"
            },
            timeout=20
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        print(f"\nWeather API error: {error}")
        return None


def display_farm_conditions():
    print("\n" + "=" * 48)
    print("       AGROVISION - FARM CONDITIONS")
    print("=" * 48)

    city = input("Enter farm city or location: ").strip()

    if not city:
        print("Location cannot be empty.")
        return

    location = get_location(city)

    if location is None:
        return

    latitude = location["latitude"]
    longitude = location["longitude"]

    weather = get_farm_conditions(latitude, longitude)

    if weather is None:
        return

    current = weather.get("current", {})
    hourly = weather.get("hourly", {})

    def show_value(data, key, unit=""):
        value = data.get(key)
        if value is None:
            return "Not Available"
        return f"{value}{unit}"

    print("\n--- Farm Location ---")
    print(f"Location: {location.get('name', city)}")
    print(f"State: {location.get('admin1', 'Not Available')}")
    print(f"Country: {location.get('country', 'Not Available')}")
    print(f"Latitude: {latitude}")
    print(f"Longitude: {longitude}")

    print("\n--- Current Weather ---")
    print(
        "Temperature:",
        show_value(current, "temperature_2m", " °C")
    )
    print(
        "Humidity:",
        show_value(current, "relative_humidity_2m", "%")
    )
    print(
        "Precipitation:",
        show_value(current, "precipitation", " mm")
    )
    print("Rain:", show_value(current, "rain", " mm"))
    print(
        "Wind Speed:",
        show_value(current, "wind_speed_10m", " km/h")
    )
    print(
        "Wind Direction:",
        show_value(current, "wind_direction_10m", " degrees")
    )

    print("\n--- Soil-Related Model Data ---")

    soil_temperature = hourly.get("soil_temperature_0cm", [])
    soil_moisture = hourly.get("soil_moisture_0_to_1cm", [])

    if soil_temperature and soil_temperature[0] is not None:
        print(
            "Modelled Soil Temperature:",
            f"{soil_temperature[0]} °C"
        )
    else:
        print("Modelled Soil Temperature: Not Available")

    if soil_moisture and soil_moisture[0] is not None:
        print(
            "Modelled Soil Moisture:",
            f"{soil_moisture[0]} m³/m³"
        )
    else:
        print("Modelled Soil Moisture: Not Available")

    print("\nNote:")
    print("Weather values are API-based estimates for the location.")
    print("Soil values are modelled data, not direct sensor readings.")
    print("These values are not the plant's ideal requirements.")
    print("\n" + "=" * 48)


if __name__ == "__main__":
    display_farm_conditions()
