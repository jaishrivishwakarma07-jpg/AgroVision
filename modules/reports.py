
import json
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style

# ============================================
# AGROVISION - Reports Management Module
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
REPORTS_DIR = BASE_DIR / "reports"

REPORT_FILES = {
    "Farmers": "farmers.json",
    "Farms": "farms.json",
    "Crops": "crops.json",
    "Soil": "soil.json",
    "Irrigation": "irrigation.json",
    "Weather": "weather.json",
}


def load_json_data(filename):
    """Load data from a JSON file safely."""

    file_path = DATABASE_DIR / filename

    if not file_path.exists():
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            # Support JSON files containing a list inside a dictionary.
            for value in data.values():
                if isinstance(value, list):
                    return value
            return [data]

        return []

    except (json.JSONDecodeError, OSError) as error:
        print(Fore.RED + f"Error reading {filename}: {error}")
        return None


def format_value(value):
    """Convert values into readable report text."""

    if value is None or value == "":
        return "N/A"

    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)

    return str(value)


def get_report_text(title, data, filename):
    """Create a readable report."""

    lines = [
        "=" * 65,
        "                 AGROVISION REPORT",
        "=" * 65,
        f"Report Type : {title}",
        f"Generated   : {datetime.now().strftime('%d-%m-%Y %I:%M:%S %p')}",
        f"Data Source : database/{filename}",
        "-" * 65,
    ]

    if data is None:
        lines.append("Database file not found.")
        lines.append("Please check the file name and database folder.")
        return "\n".join(lines)

    if not data:
        lines.append("No records found.")
        return "\n".join(lines)

    lines.append(f"Total Records: {len(data)}")
    lines.append("-" * 65)

    for index, record in enumerate(data, start=1):
        lines.append(f"\nRecord {index}")
        lines.append("-" * 30)

        if isinstance(record, dict):
            for key, value in record.items():
                readable_key = key.replace("_", " ").title()
                lines.append(f"{readable_key}: {format_value(value)}")
        else:
            lines.append(format_value(record))

    lines.append("\n" + "=" * 65)
    lines.append("             End of Report")
    lines.append("=" * 65)

    return "\n".join(lines)


def display_report(title, filename):
    """Display a selected report."""

    data = load_json_data(filename)
    report_text = get_report_text(title, data, filename)

    print("\n" + Fore.CYAN + report_text + Style.RESET_ALL)

    return report_text


def save_report(report_text, title):
    """Save a report as a text file."""

    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = title.lower().replace(" ", "_")
        file_path = REPORTS_DIR / f"{safe_title}_{timestamp}.txt"

        with open(file_path, "w", encoding="utf-8") as file:
            file.write(report_text)

        print(Fore.GREEN + f"\nReport saved successfully!")
        print(f"File: {file_path}")

    except OSError as error:
        print(Fore.RED + f"\nUnable to save report: {error}")


def overall_summary():
    """Display a summary of available database records."""

    print(Fore.CYAN + "\n========== AGROVISION OVERALL SUMMARY ==========")

    total_records = 0

    for title, filename in REPORT_FILES.items():
        data = load_json_data(filename)

        if data is None:
            print(f"{title:<15}: Database file not found")
        else:
            count = len(data)
            total_records += count
            print(f"{title:<15}: {count} records")

    print("-" * 48)
    print(f"{'Total Records':<15}: {total_records}")
    print(Fore.CYAN + "=" * 48)


def reports_menu():
    """Main reports menu."""

    while True:
        print(Fore.GREEN + "\n================================================")
        print(Fore.CYAN + "             AGROVISION REPORTS")
        print(Fore.GREEN + "================================================")

        print("1. Farmer Report")
        print("2. Farm Report")
        print("3. Crop Report")
        print("4. Soil Report")
        print("5. Irrigation Report")
        print("6. Weather Report")
        print("7. Overall Summary")
        print("8. Save a Report")
        print("9. Back to Dashboard")

        print(Fore.GREEN + "================================================")

        choice = input("Enter your choice: ").strip()

        report_options = {
            "1": ("Farmers", "farmers.json"),
            "2": ("Farms", "farms.json"),
            "3": ("Crops", "crops.json"),
            "4": ("Soil", "soil.json"),
            "5": ("Irrigation", "irrigation.json"),
            "6": ("Weather", "weather.json"),
        }

        if choice in report_options:
            title, filename = report_options[choice]
            report_text = display_report(title, filename)

            save_choice = input(
                "\nDo you want to save this report? (y/n): "
            ).strip().lower()

            if save_choice == "y":
                save_report(report_text, title)

        elif choice == "7":
            overall_summary()

        elif choice == "8":
            print("\nChoose a report to save:")
            print("1. Farmer Report")
            print("2. Farm Report")
            print("3. Crop Report")
            print("4. Soil Report")
            print("5. Irrigation Report")
            print("6. Weather Report")

            save_choice = input("Enter choice: ").strip()

            if save_choice in report_options:
                title, filename = report_options[save_choice]
                report_text = display_report(title, filename)
                save_report(report_text, title)
            else:
                print(Fore.RED + "Invalid choice!")

        elif choice == "9":
            print(Fore.YELLOW + "\nReturning to Admin Dashboard...")
            break

        else:
            print(Fore.RED + "\nInvalid choice! Please try again.")
