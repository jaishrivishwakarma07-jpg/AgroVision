
import subprocess
import sys
import time
import webbrowser
import json
from pathlib import Path
from collections import Counter

from colorama import Fore, Style

from modules.farmer import farmer_management
from modules.farm import farm_management
from modules.crop import crop_management
from modules.soil import soil_management
from modules.weather import weather_management
from modules.fertilizer import fertilizer_management
from modules.disease import disease_management
from modules.irrigation import irrigation_management
from modules.market import market_price_menu
from modules.reports import reports_menu


# ============================================
# PROJECT PATHS
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
APP_FILE = BASE_DIR / "web" / "app.py"


# ============================================
# DATABASE HELPER
# ============================================

def load_json_data(filename):
    """Safely load a JSON database file."""

    file_path = DATABASE_DIR / filename

    if not file_path.exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    return value
            return [data]

        return []

    except (json.JSONDecodeError, OSError) as error:
        print(Fore.RED + f"Could not read {filename}: {error}")
        return []


def get_value(record, *keys):
    """Get the first available non-empty field."""

    if not isinstance(record, dict):
        return "Unknown"

    for key in keys:
        value = record.get(key)

        if value is not None and str(value).strip():
            return str(value).strip()

    return "Unknown"


# ============================================
# DASHBOARD ANALYTICS
# ============================================

def dashboard_analytics():

    while True:
        farmers = load_json_data("farmers.json")
        farms = load_json_data("farms.json")
        crops = load_json_data("crops.json")
        soil_records = load_json_data("soil.json")
        irrigation_records = load_json_data("irrigation.json")
        weather_records = load_json_data("weather.json")
        disease_records = load_json_data("disease.json")
        fertilizer_records = load_json_data("fertilizer.json")

        print(Fore.GREEN + "\n" + "=" * 58)
        print(Fore.CYAN + "             AGROVISION DASHBOARD ANALYTICS")
        print(Fore.GREEN + "=" * 58 + Style.RESET_ALL)

        print("\n               RECORD SUMMARY")
        print("-" * 58)

        summary = [
            ("Total Farmers", farmers),
            ("Total Farms", farms),
            ("Total Crops", crops),
            ("Soil Reports", soil_records),
            ("Irrigation Records", irrigation_records),
            ("Weather Records", weather_records),
            ("Disease Records", disease_records),
            ("Fertilizer Records", fertilizer_records),
        ]

        for label, records in summary:
            print(f"{label:<28}: {len(records)}")

        print("\n               CROP ANALYTICS")
        print("-" * 58)

        if crops:
            status_counts = Counter(
                get_value(record, "status").title()
                for record in crops
            )

            season_counts = Counter(
                get_value(record, "season").title()
                for record in crops
            )

            stage_counts = Counter(
                get_value(record, "stage").title()
                for record in crops
            )

            print("\nCrop Status:")
            for status, count in status_counts.items():
                print(f"  {status:<24}: {count}")

            print("\nCrop Season:")
            for season, count in season_counts.items():
                print(f"  {season:<24}: {count}")

            print("\nCrop Growth Stage:")
            for stage, count in stage_counts.items():
                print(f"  {stage:<24}: {count}")

            print("\nCrop Details:")
            for record in crops:
                crop_name = get_value(record, "crop_name", "name")
                crop_id = get_value(record, "crop_id", "id")
                status = get_value(record, "status")
                season = get_value(record, "season")

                print(
                    f"  {crop_id} | {crop_name} | "
                    f"{season} | {status}"
                )
        else:
            print("No crop records available.")

        print("\n               FARM ANALYTICS")
        print("-" * 58)

        if farms:
            district_counts = Counter(
                get_value(record, "district").title()
                for record in farms
            )

            print("\nFarms by District:")
            for district, count in district_counts.items():
                print(f"  {district:<24}: {count}")

            total_area = 0.0
            valid_area_count = 0

            for farm in farms:
                try:
                    area = float(farm.get("area", 0))
                    total_area += area
                    valid_area_count += 1
                except (TypeError, ValueError):
                    continue

            if valid_area_count:
                print(f"\nRecorded Total Farm Area: {total_area:g}")
                print("Note: Area unit is not specified in the records.")
        else:
            print("No farm records available.")

        print("\n               IRRIGATION ANALYTICS")
        print("-" * 58)

        if irrigation_records:
            irrigation_statuses = Counter(
                get_value(record, "status").title()
                for record in irrigation_records
            )

            for status, count in irrigation_statuses.items():
                print(f"  {status:<24}: {count}")
        else:
            print("No irrigation records available.")

        print("\n               RECENT RECORDS")
        print("-" * 58)

        recent_groups = [
            ("Farmer", farmers, ("name", "farmer_name")),
            ("Farm", farms, ("farm_name", "farm_id")),
            ("Crop", crops, ("crop_name", "name")),
            ("Soil", soil_records, ("soil_id", "soil_type")),
            ("Irrigation", irrigation_records, ("crop_name", "farm_id")),
            ("Weather", weather_records, ("city", "location")),
        ]

        found_recent = False

        for label, records, keys in recent_groups:
            if records:
                record_name = get_value(records[-1], *keys)
                print(f"{label:<15}: {record_name}")
                found_recent = True

        if not found_recent:
            print("No recent records available.")

        print("\n" + "=" * 58)
        print("1. Refresh Analytics")
        print("2. Back to Admin Dashboard")
        print("=" * 58)

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            continue

        elif choice == "2":
            break

        else:
            print(Fore.RED + "\nInvalid choice. Please enter 1 or 2.")
            input("Press Enter to continue...")


# ============================================
# AI PLANT SCANNER
# ============================================

def open_plant_scanner():
    """Start the existing Flask scanner and open it."""

    if not APP_FILE.exists():
        print(Fore.RED + "\nError: web/app.py file nahi mili.")
        input("\nPress Enter to continue...")
        return

    try:
        import requests

        url = "http://127.0.0.1:5000"
        server_running = False

        try:
            response = requests.get(
                url + "/api/status",
                timeout=2
            )
            server_running = response.ok
        except requests.RequestException:
            pass

        if not server_running:
            print(Fore.CYAN + "\nStarting AGROVISION AI Plant Scanner...")

            subprocess.Popen(
                [sys.executable, str(APP_FILE)],
                cwd=str(BASE_DIR)
            )

            for _ in range(20):
                time.sleep(1)

                try:
                    response = requests.get(
                        url + "/api/status",
                        timeout=2
                    )

                    if response.ok:
                        server_running = True
                        break

                except requests.RequestException:
                    continue

        if server_running:
            webbrowser.open(url)
            print(Fore.GREEN + "\nAI Plant Scanner browser mein open ho raha hai.")
            print(Fore.CYAN + "URL: " + url)
        else:
            print(Fore.RED + "\nScanner server start nahi hua.")
            print("Terminal mein Flask/API error check karo.")

    except Exception as error:
        print(Fore.RED + f"\nScanner error: {error}")

    input("\nPress Enter to return to Admin Dashboard...")


# ============================================
# ADMIN DASHBOARD
# ============================================

def admin_dashboard():

    while True:
        print(Fore.GREEN + "\n" + "=" * 58)
        print(Fore.CYAN + "             AGROVISION ADMIN DASHBOARD")
        print(Fore.GREEN + "=" * 58 + Style.RESET_ALL)

        print("1. Farmer Management")
        print("2. Farm Management")
        print("3. Crop Management")
        print("4. Soil Management")
        print("5. Weather Management")
        print("6. Fertilizer Recommendation")
        print("7. Disease Detection")
        print("8. Irrigation Management")
        print("9. Market Price")
        print("10. Reports")
        print("11. Dashboard Analytics")
        print("12. AI Plant Scanner")
        print("13. Logout")

        print(Fore.GREEN + "=" * 58 + Style.RESET_ALL)

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            farmer_management()

        elif choice == "2":
            farm_management()

        elif choice == "3":
            crop_management()

        elif choice == "4":
            soil_management()

        elif choice == "5":
            weather_management()

        elif choice == "6":
            fertilizer_management()

        elif choice == "7":
            disease_management()

        elif choice == "8":
            irrigation_management()

        elif choice == "9":
            market_price_menu()

        elif choice == "10":
            reports_menu()

        elif choice == "11":
            dashboard_analytics()

        elif choice == "12":
            open_plant_scanner()

        elif choice == "13":
            print(Fore.RED + "\nLogging Out...")
            break

        else:
            print(Fore.RED + "\nInvalid Choice!")
            input("Press Enter to continue...")
