
import json
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style

# ============================================
# AGROVISION - Irrigation Management
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
IRRIGATION_FILE = DATABASE_DIR / "irrigation.json"


def load_irrigation_records():
    """Load irrigation records from JSON."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    if not IRRIGATION_FILE.exists():
        return []

    try:
        with open(IRRIGATION_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        print(Fore.RED + "\nError reading irrigation.json.")
        return []


def save_irrigation_records(records):
    """Save irrigation records to JSON."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    with open(IRRIGATION_FILE, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=4, ensure_ascii=False)


def get_next_id(records):
    """Generate the next irrigation record ID."""
    existing_ids = []

    for record in records:
        record_id = record.get("irrigation_id", "")
        if record_id.startswith("IR") and record_id[2:].isdigit():
            existing_ids.append(int(record_id[2:]))

    return f"IR{max(existing_ids, default=0) + 1:03d}"


def add_irrigation_record():
    """Add a new irrigation schedule or record."""
    print(Fore.CYAN + "\n========== ADD IRRIGATION RECORD ==========")

    records = load_irrigation_records()

    farm_id = input("Enter Farm ID: ").strip()
    crop_name = input("Enter Crop Name: ").strip()
    irrigation_date = input("Enter Irrigation Date (DD-MM-YYYY): ").strip()

    try:
        datetime.strptime(irrigation_date, "%d-%m-%Y")
    except ValueError:
        print(Fore.RED + "\nInvalid date. Use DD-MM-YYYY format.")
        return

    try:
        water_liters = float(input("Enter Water Quantity (liters): "))
        if water_liters <= 0:
            print(Fore.RED + "\nWater quantity must be greater than zero.")
            return

        duration_minutes = int(input("Enter Duration (minutes): "))
        if duration_minutes <= 0:
            print(Fore.RED + "\nDuration must be greater than zero.")
            return

    except ValueError:
        print(Fore.RED + "\nPlease enter valid numeric values.")
        return

    notes = input("Enter Notes (optional): ").strip()

    new_record = {
        "irrigation_id": get_next_id(records),
        "farm_id": farm_id,
        "crop_name": crop_name,
        "irrigation_date": irrigation_date,
        "water_liters": water_liters,
        "duration_minutes": duration_minutes,
        "status": "Scheduled",
        "notes": notes
    }

    records.append(new_record)
    save_irrigation_records(records)

    print(Fore.GREEN + "\nIrrigation record saved successfully!")
    print("Irrigation ID:", new_record["irrigation_id"])


def view_irrigation_records():
    """Display all irrigation records."""
    print(Fore.CYAN + "\n========== IRRIGATION RECORDS ==========")

    records = load_irrigation_records()

    if not records:
        print(Fore.YELLOW + "\nNo irrigation records found.")
        return

    for record in records:
        print("\n" + "-" * 45)
        print("Irrigation ID :", record.get("irrigation_id", "N/A"))
        print("Farm ID       :", record.get("farm_id", "N/A"))
        print("Crop          :", record.get("crop_name", "N/A"))
        print("Date          :", record.get("irrigation_date", "N/A"))
        print("Water (liters):", record.get("water_liters", "N/A"))
        print("Duration      :", record.get("duration_minutes", "N/A"), "minutes")
        print("Status        :", record.get("status", "N/A"))
        print("Notes         :", record.get("notes", ""))

    print("-" * 45)


def update_irrigation_status():
    """Update the status of an irrigation record."""
    print(Fore.CYAN + "\n========== UPDATE IRRIGATION STATUS ==========")

    records = load_irrigation_records()

    if not records:
        print(Fore.YELLOW + "\nNo irrigation records available.")
        return

    irrigation_id = input("Enter Irrigation ID (e.g. IR001): ").strip().upper()

    for record in records:
        if record.get("irrigation_id", "").upper() == irrigation_id:
            print("\n1. Scheduled")
            print("2. In Progress")
            print("3. Completed")
            print("4. Cancelled")

            choice = input("Select new status: ").strip()

            statuses = {
                "1": "Scheduled",
                "2": "In Progress",
                "3": "Completed",
                "4": "Cancelled"
            }

            if choice not in statuses:
                print(Fore.RED + "\nInvalid status choice.")
                return

            record["status"] = statuses[choice]
            save_irrigation_records(records)

            print(Fore.GREEN + "\nIrrigation status updated successfully!")
            return

    print(Fore.RED + "\nIrrigation ID not found.")


def irrigation_advice():
    """Provide a simple rule-based irrigation suggestion."""
    print(Fore.CYAN + "\n========== IRRIGATION ADVISOR ==========")
    print("Enter the soil moisture percentage from a reliable measurement.")
    print("This is a basic rule-based suggestion, not an AI or sensor reading.")

    try:
        moisture = float(input("Soil Moisture (%): "))

        if not 0 <= moisture <= 100:
            print(Fore.RED + "\nMoisture must be between 0 and 100.")
            return

    except ValueError:
        print(Fore.RED + "\nPlease enter a valid percentage.")
        return

    rain_forecast = input("Is rain expected soon? (yes/no): ").strip().lower()

    if rain_forecast not in ("yes", "no"):
        print(Fore.RED + "\nPlease enter yes or no.")
        return

    print(Fore.CYAN + "\n---------- SUGGESTION ----------")

    if moisture < 20:
        if rain_forecast == "yes":
            print(Fore.YELLOW +
                  "Soil moisture is low, but rain is expected. "
                  "Check the field and forecast before irrigating.")
        else:
            print(Fore.YELLOW +
                  "Soil moisture is low. Check crop needs and field "
                  "conditions; irrigation may be needed.")

    elif moisture < 40:
        if rain_forecast == "yes":
            print(Fore.YELLOW +
                  "Check the crop and upcoming rainfall before scheduling irrigation.")
        else:
            print(Fore.GREEN +
                  "Monitor soil moisture and crop condition to decide when to irrigate.")

    else:
        print(Fore.GREEN +
              "Measured moisture is relatively high. Check crop requirements "
              "and field conditions before adding more water.")

    print(Style.RESET_ALL)
    print("Note: Thresholds are generic examples. Suitable moisture varies by crop,")
    print("soil type, growth stage, and measurement method.")


def irrigation_management():
    """Main irrigation management menu."""
    while True:
        print(Fore.GREEN + "\n================================================")
        print(Fore.CYAN + "          AGROVISION IRRIGATION MANAGEMENT")
        print(Fore.GREEN + "================================================")

        print("1. Add Irrigation Record")
        print("2. View Irrigation Records")
        print("3. Update Irrigation Status")
        print("4. Irrigation Advisor")
        print("5. Back to Admin Dashboard")

        print(Fore.GREEN + "================================================")

        choice = input("Enter your choice: ").strip()

        if choice == "1":
            add_irrigation_record()

        elif choice == "2":
            view_irrigation_records()

        elif choice == "3":
            update_irrigation_status()

        elif choice == "4":
            irrigation_advice()

        elif choice == "5":
            print(Fore.YELLOW + "\nReturning to Admin Dashboard...")
            break

        else:
            print(Fore.RED + "\nInvalid choice. Please try again.")


if __name__ == "__main__":
    irrigation_management()
