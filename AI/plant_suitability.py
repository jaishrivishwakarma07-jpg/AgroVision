
import requests

from plant_requirements import get_plant_requirements


WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(latitude, longitude):
    """Fetch current weather and daily forecast."""

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "wind_speed_10m,"
            "rain,"
            "soil_temperature_0cm,"
            "soil_moisture_0_to_1cm,"
            "et0_fao_evapotranspiration,"
            "vapour_pressure_deficit"
        ),
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "sunrise,"
            "sunset,"
            "sunshine_duration,"
            "precipitation_sum,"
            "precipitation_probability_max"
        ),
        "forecast_days": 7,
        "timezone": "auto",
    }

    response = requests.get(
        WEATHER_URL,
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("current"):
        raise ValueError("Current weather data is unavailable.")

    return data


def format_value(value, unit=""):
    if value is None:
        return "Not Available"

    if isinstance(value, (int, float)):
        return f"{value:.2f}{unit}"

    return f"{value}{unit}"


def display_current_weather(current):
    print("\nLIVE ENVIRONMENT")
    print("-" * 65)

    fields = [
        ("Temperature", "temperature_2m", " °C"),
        ("Humidity", "relative_humidity_2m", " %"),
        ("Wind Speed", "wind_speed_10m", " km/h"),
        ("Current Rain", "rain", " mm"),
        ("Soil Temperature", "soil_temperature_0cm", " °C"),
        ("Soil Moisture", "soil_moisture_0_to_1cm", " m³/m³"),
        ("Evapotranspiration ET0", "et0_fao_evapotranspiration", " mm"),
        ("Vapour Pressure Deficit", "vapour_pressure_deficit", " kPa"),
    ]

    for label, key, unit in fields:
        print(f"{label:<30}: {format_value(current.get(key), unit)}")


def display_forecast(daily):
    print("\n7-DAY WEATHER FORECAST")
    print("-" * 90)

    if not daily or not daily.get("time"):
        print("Daily forecast unavailable.")
        return

    dates = daily.get("time", [])

    fields = [
        ("temperature_2m_max", "Max Temp (°C)"),
        ("temperature_2m_min", "Min Temp (°C)"),
        ("sunshine_duration", "Sunshine (hours)"),
        ("precipitation_sum", "Rain (mm)"),
        ("precipitation_probability_max", "Rain Chance (%)"),
    ]

    for index, date in enumerate(dates):
        print(f"\nDate: {date}")

        for key, label in fields:
            values = daily.get(key, [])
            value = values[index] if index < len(values) else None

            if key == "sunshine_duration" and value is not None:
                value = value / 3600
                formatted = format_value(value, " hours")
            elif key == "precipitation_probability_max":
                formatted = format_value(value, "%")
            elif key == "precipitation_sum":
                formatted = format_value(value, " mm")
            else:
                formatted = format_value(value, " °C")

            print(f"  {label:<22}: {formatted}")

        for key, label in [
            ("sunrise", "Sunrise"),
            ("sunset", "Sunset"),
        ]:
            values = daily.get(key, [])
            value = values[index] if index < len(values) else None
            print(f"  {label:<22}: {value or 'Not Available'}")


def display_plant_checks(profile, current, daily):
    print("\nPLANT REQUIREMENT CHECKS")
    print("-" * 65)

    minimum = profile.get("temperature_min")
    maximum = profile.get("temperature_max")
    temperature = current.get("temperature_2m")

    if (
        isinstance(minimum, (int, float))
        and isinstance(maximum, (int, float))
        and isinstance(temperature, (int, float))
    ):
        if minimum <= temperature <= maximum:
            print("Temperature: Within recorded range")
        else:
            print("Temperature: Outside recorded range")
    else:
        print(
            "Temperature: Insufficient data - "
            "verified plant temperature limits unavailable"
        )

    sunlight = profile.get("sunlight", "Not Available")

    if sunlight != "Not Available":
        print(f"Sunlight requirement: {sunlight}")

        sunshine = daily.get("sunshine_duration", [])
        if sunshine and sunshine[0] is not None:
            hours = sunshine[0] / 3600
            print(
                f"Forecast sunshine duration today: "
                f"{hours:.2f} hours"
            )
            print(
                "Note: Sunshine duration is not necessarily "
                "equal to direct sunlight received by the plant."
            )
        else:
            print("Sunshine duration: Not Available")
    else:
        print("Sunlight requirement: Not Available")

    soil_type = profile.get("soil_type", "Not Available")

    if soil_type != "Not Available":
        print(f"Preferred soil: {soil_type}")
        print("Actual soil type: Not measured")
    else:
        print("Preferred soil: Not Available")

    print("Soil pH: Cannot assess without a soil pH measurement.")

    soil_moisture = current.get("soil_moisture_0_to_1cm")
    if soil_moisture is not None:
        print(
            f"Open-Meteo soil moisture (0-1 cm): "
            f"{soil_moisture:.3f} m³/m³"
        )
        print(
            "Plant-specific soil moisture limits: "
            "Not Available"
        )
    else:
        print("Soil moisture: Not Available")


def show_report(plant_name, latitude, longitude, profile, weather):
    current = weather["current"]
    daily = weather.get("daily", {})

    print("\n" + "=" * 65)
    print("AGROVISION - PLANT SUITABILITY REPORT")
    print("=" * 65)

    print("Plant          :", profile.get("common_name"))
    print("Scientific Name:", profile.get("scientific_name"))
    print("Data Status    :", profile.get("data_status"))
    print("Latitude       :", latitude)
    print("Longitude      :", longitude)

    display_current_weather(current)
    display_forecast(daily)
    display_plant_checks(profile, current, daily)

    print("\nOVERALL RESULT")
    print("-" * 65)
    print("Status: INSUFFICIENT DATA FOR A COMPLETE SUITABILITY VERDICT")
    print(
        "Reason: Some verified plant-specific limits and actual "
        "soil measurements are missing."
    )
    print("Plant data source:", profile.get("source", "Not Available"))
    print("Weather source: Open-Meteo")
    print("=" * 65)


def main():
    print("\nAGROVISION - LIVE PLANT SUITABILITY")
    print("-" * 65)

    plant_name = input(
        "Enter plant scientific name: "
    ).strip()

    if not plant_name:
        print("Plant name cannot be empty.")
        return

    try:
        latitude = float(input("Enter latitude: ").strip())
        longitude = float(input("Enter longitude: ").strip())

        if not -90 <= latitude <= 90:
            print("Latitude must be between -90 and 90.")
            return

        if not -180 <= longitude <= 180:
            print("Longitude must be between -180 and 180.")
            return

    except ValueError:
        print("Please enter valid numeric coordinates.")
        return

    print("\nFetching plant profile...")

    try:
        profile = get_plant_requirements(plant_name)
    except Exception as error:
        print(f"Plant profile error: {error}")
        return

    print("Fetching current weather and 7-day forecast...")

    try:
        weather = get_weather(latitude, longitude)
    except (requests.RequestException, ValueError) as error:
        print(f"Weather request failed: {error}")
        return

    show_report(
        plant_name,
        latitude,
        longitude,
        profile,
        weather,
    )


if __name__ == "__main__":
    main()
