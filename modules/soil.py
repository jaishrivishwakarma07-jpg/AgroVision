import json
import os
from colorama import Fore

FILE_NAME = "database/soil.json"


# ==========================================
# Load Soil Reports
# ==========================================

def load_soil():

    if not os.path.exists(FILE_NAME):
        return []

    try:
        with open(FILE_NAME, "r") as file:
            return json.load(file)
    except:
        return []


# ==========================================
# Save Soil Reports
# ==========================================

def save_soil(data):

    with open(FILE_NAME, "w") as file:
        json.dump(data, file, indent=4)


# ==========================================
# Generate Soil ID
# ==========================================

def generate_soil_id():

    data = load_soil()

    if len(data) == 0:
        return "S001"

    last_id = data[-1]["soil_id"]

    number = int(last_id[1:]) + 1

    return f"S{number:03d}"


# ==========================================
# Add Soil Report
# ==========================================

def add_soil():

    print(Fore.CYAN + "\n========== ADD SOIL REPORT ==========\n")

    soil_reports = load_soil()

    report = {

        "soil_id": generate_soil_id(),
        "farm_id": input("Farm ID              : "),
        "soil_type": input("Soil Type            : "),
        "ph": input("Soil pH              : "),
        "nitrogen": input("Nitrogen (N)         : "),
        "phosphorus": input("Phosphorus (P)       : "),
        "potassium": input("Potassium (K)        : "),
        "organic_carbon": input("Organic Carbon       : "),
        "moisture": input("Moisture (%)         : "),
        "temperature": input("Temperature (°C)     : "),
        "report_date": input("Report Date          : ")

    }

    soil_reports.append(report)

    save_soil(soil_reports)

    print(Fore.GREEN + "\nSoil Report Added Successfully!")
    
    

# ==========================================
# View Soil Reports
# ==========================================

def view_soil():

    soil_reports = load_soil()

    print(Fore.CYAN + "\n========== SOIL REPORTS ==========\n")

    if len(soil_reports) == 0:
        print(Fore.RED + "No Soil Reports Found!")
        return

    print("-"*140)

    print(
        f"{'ID':<8}"
        f"{'Farm':<10}"
        f"{'Type':<15}"
        f"{'pH':<8}"
        f"{'N':<10}"
        f"{'P':<10}"
        f"{'K':<10}"
        f"{'Moisture':<12}"
        f"{'Temp'}"
    )

    print("-"*140)

    for report in soil_reports:

        print(
            f"{report['soil_id']:<8}"
            f"{report['farm_id']:<10}"
            f"{report['soil_type']:<15}"
            f"{report['ph']:<8}"
            f"{report['nitrogen']:<10}"
            f"{report['phosphorus']:<10}"
            f"{report['potassium']:<10}"
            f"{report['moisture']:<12}"
            f"{report['temperature']}"
        )

    print("-"*140)
    
    
# ==========================================
# Search Soil Report
# ==========================================

def search_soil():

    soil_id = input("\nEnter Soil ID : ")

    soil_reports = load_soil()

    for report in soil_reports:

        if report["soil_id"] == soil_id:

            print("\nSoil Report Found\n")

            for key, value in report.items():
                print(f"{key} : {value}")

            return

    print(Fore.RED + "\nSoil Report Not Found!")
    
    
# ==========================================
# Delete Soil Report
# ==========================================

def delete_soil():

    soil_id = input("\nEnter Soil ID : ")

    soil_reports = load_soil()

    for report in soil_reports:

        if report["soil_id"] == soil_id:

            soil_reports.remove(report)

            save_soil(soil_reports)

            print(Fore.GREEN + "\nSoil Report Deleted Successfully!")

            return

    print(Fore.RED + "\nSoil Report Not Found!")
    
    
# ==========================================
# Soil Health Analysis
# ==========================================

def soil_health():

    print(Fore.CYAN + "\n========== SOIL HEALTH ANALYSIS ==========\n")

    ph = float(input("Enter Soil pH : "))

    if ph < 6:
        print(Fore.RED + "\nAcidic Soil")
        print("Recommendation : Add Lime")

    elif ph <= 7.5:
        print(Fore.GREEN + "\nHealthy Soil")
        print("Recommendation : Suitable for most crops")

    else:
        print(Fore.YELLOW + "\nAlkaline Soil")
        print("Recommendation : Add Organic Compost")
        
        
        
# ==========================================
# Soil Management Menu
# ==========================================

def soil_management():

    while True:

        print(Fore.GREEN + "\n====================================")
        print(Fore.CYAN + "        SOIL MANAGEMENT")
        print(Fore.GREEN + "====================================")

        print("1. Add Soil Report")
        print("2. View Soil Reports")
        print("3. Search Soil Report")
        print("4. Delete Soil Report")
        print("5. Soil Health Analysis")
        print("6. Back")

        choice = input("\nEnter Your Choice : ")

        if choice == "1":
            add_soil()

        elif choice == "2":
            view_soil()

        elif choice == "3":
            search_soil()

        elif choice == "4":
            delete_soil()

        elif choice == "5":
            soil_health()

        elif choice == "6":
            break

        else:
            print(Fore.RED + "\nInvalid Choice!")