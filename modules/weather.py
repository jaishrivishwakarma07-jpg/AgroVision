import json
import os
import sys
from colorama import Fore, Style


# ==========================================
# UTF-8 SUPPORT FOR WINDOWS
# ==========================================

if sys.platform == "win32":

    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except:
        pass


# ==========================================
# FILE PATH
# ==========================================

FILE_NAME = "database/weather.json"


# ==========================================
# Load Weather Data
# ==========================================

def load_weather():

    if not os.path.exists(FILE_NAME):
        return []

    try:

        with open(FILE_NAME, "r", encoding="utf-8") as file:
            return json.load(file)

    except:

        return []


# ==========================================
# Save Weather Data
# ==========================================

def save_weather(data):

    # Create database folder if it does not exist
    os.makedirs("database", exist_ok=True)

    with open(FILE_NAME, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


# ==========================================
# Add Weather
# ==========================================

def add_weather():

    print(
        Fore.CYAN +
        "\n========== ADD WEATHER ==========\n"
    )

    # City
    while True:

        city = input("City                 : ").strip()

        if city != "":
            break

        print(Fore.RED + "City cannot be empty!")


    # Temperature
    while True:

        temperature = input(
            "Temperature (°C)     : "
        ).strip()

        try:

            temperature_value = float(
                temperature.replace("°C", "").strip()
            )

            # Save with °C
            if temperature_value.is_integer():
                temperature = f"{int(temperature_value)}°C"
            else:
                temperature = f"{temperature_value}°C"

            break

        except:

            print(
                Fore.RED +
                "Please enter a valid temperature!"
            )


    # Humidity
    while True:

        humidity = input(
            "Humidity (%)         : "
        ).strip()

        try:

            humidity_value = float(
                humidity.replace("%", "").strip()
            )

            if 0 <= humidity_value <= 100:

                if humidity_value.is_integer():
                    humidity = f"{int(humidity_value)}%"
                else:
                    humidity = f"{humidity_value}%"

                break

        except:
            pass

        print(
            Fore.RED +
            "Humidity must be between 0 and 100!"
        )


    # Rain Chance
    while True:

        rain = input(
            "Rain Chance (%)      : "
        ).strip()

        try:

            rain_value = float(
                rain.replace("%", "").strip()
            )

            if 0 <= rain_value <= 100:

                if rain_value.is_integer():
                    rain = f"{int(rain_value)}%"
                else:
                    rain = f"{rain_value}%"

                break

        except:
            pass

        print(
            Fore.RED +
            "Rain chance must be between 0 and 100!"
        )


    # Wind Speed
    while True:

        wind = input(
            "Wind Speed (km/h)    : "
        ).strip()

        try:

            wind_value = float(
                wind.replace("km/h", "").strip()
            )

            if wind_value >= 0:

                if wind_value.is_integer():
                    wind = f"{int(wind_value)} km/h"
                else:
                    wind = f"{wind_value} km/h"

                break

        except:
            pass

        print(
            Fore.RED +
            "Please enter a valid wind speed!"
        )


    # Weather Condition
    while True:

        condition = input(
            "Condition            : "
        ).strip()

        if condition != "":
            condition = condition.capitalize()
            break

        print(
            Fore.RED +
            "Condition cannot be empty!"
        )


    # ==========================================
    # Create Weather Record
    # ==========================================

    weather = {

        "city": city,
        "temperature": temperature,
        "humidity": humidity,
        "rain": rain,
        "wind": wind,
        "condition": condition

    }


    # ==========================================
    # Save Record
    # ==========================================

    weather_data = load_weather()

    weather_data.append(weather)

    save_weather(weather_data)


    # ==========================================
    # Display Added Weather
    # ==========================================

    print(
        Fore.GREEN +
        "\nWeather Report Added Successfully!\n"
    )

    print(
        Fore.YELLOW +
        "City                 : " +
        Fore.WHITE +
        city
    )

    print(
        Fore.YELLOW +
        "Temperature (°C)     : " +
        Fore.WHITE +
        temperature
    )

    print(
        Fore.YELLOW +
        "Humidity (%)         : " +
        Fore.WHITE +
        humidity
    )

    print(
        Fore.YELLOW +
        "Rain Chance (%)      : " +
        Fore.WHITE +
        rain
    )

    print(
        Fore.YELLOW +
        "Wind Speed (km/h)    : " +
        Fore.WHITE +
        wind
    )

    print(
        Fore.YELLOW +
        "Condition            : " +
        Fore.WHITE +
        condition
    )

    print()


# ==========================================
# View Weather
# ==========================================

def view_weather():

    weather_data = load_weather()

    print(
        Fore.CYAN +
        "\n========== WEATHER REPORTS ==========\n"
    )

    if len(weather_data) == 0:

        print(
            Fore.RED +
            "No Weather Records Found!"
        )

        return


    print("-" * 100)

    print(
        f"{'No.':<6}"
        f"{'City':<18}"
        f"{'Temperature':<16}"
        f"{'Humidity':<12}"
        f"{'Rain':<12}"
        f"{'Wind':<15}"
        f"{'Condition'}"
    )

    print("-" * 100)


    for index, weather in enumerate(
        weather_data,
        start=1
    ):

        print(
            f"{index:<6}"
            f"{weather.get('city', ''):<18}"
            f"{weather.get('temperature', ''):<16}"
            f"{weather.get('humidity', ''):<12}"
            f"{weather.get('rain', ''):<12}"
            f"{weather.get('wind', ''):<15}"
            f"{weather.get('condition', '')}"
        )


    print("-" * 100)


# ==========================================
# Search Weather
# ==========================================

def search_weather():

    print(
        Fore.CYAN +
        "\n========== SEARCH WEATHER ==========\n"
    )

    city = input(
        "Enter City Name : "
    ).strip().lower()


    weather_data = load_weather()


    found = False


    for weather in weather_data:

        if weather.get("city", "").lower() == city:

            found = True

            print(
                Fore.GREEN +
                "\nWeather Report Found!\n"
            )

            print(
                "City                 :",
                weather.get("city", "")
            )

            print(
                "Temperature (°C)     :",
                weather.get("temperature", "")
            )

            print(
                "Humidity (%)         :",
                weather.get("humidity", "")
            )

            print(
                "Rain Chance (%)      :",
                weather.get("rain", "")
            )

            print(
                "Wind Speed (km/h)    :",
                weather.get("wind", "")
            )

            print(
                "Condition            :",
                weather.get("condition", "")
            )

            print()

            break


    if not found:

        print(
            Fore.RED +
            "\nWeather Report Not Found!"
        )


# ==========================================
# Delete Weather
# ==========================================

def delete_weather():

    print(
        Fore.CYAN +
        "\n========== DELETE WEATHER ==========\n"
    )

    city = input(
        "Enter City Name : "
    ).strip().lower()


    weather_data = load_weather()


    for weather in weather_data:

        if weather.get("city", "").lower() == city:

            weather_data.remove(weather)

            save_weather(weather_data)

            print(
                Fore.GREEN +
                "\nWeather Report Deleted Successfully!"
            )

            return


    print(
        Fore.RED +
        "\nWeather Report Not Found!"
    )


# ==========================================
# Weather Management Menu
# ==========================================

def weather_management():

    while True:

        print(
            Fore.GREEN +
            "\n===================================="
        )

        print(
            Fore.CYAN +
            "        WEATHER MANAGEMENT"
        )

        print(
            Fore.GREEN +
            "===================================="
        )

        print(
            Fore.WHITE +
            "1. Add Weather"
        )

        print(
            Fore.WHITE +
            "2. View Weather"
        )

        print(
            Fore.WHITE +
            "3. Search Weather"
        )

        print(
            Fore.WHITE +
            "4. Delete Weather"
        )

        print(
            Fore.WHITE +
            "5. Back"
        )


        choice = input(
            "\nEnter Your Choice : "
        ).strip()


        if choice == "1":

            add_weather()


        elif choice == "2":

            view_weather()


        elif choice == "3":

            search_weather()


        elif choice == "4":

            delete_weather()


        elif choice == "5":

            break


        else:

            print(
                Fore.RED +
                "\nInvalid Choice!"
            )