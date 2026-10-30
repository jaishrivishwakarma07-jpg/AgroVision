import json
import os
from colorama import Fore

FILE_NAME = "database/farms.json"


# ==========================================
# Load Farms
# ==========================================

def load_farms():

    if not os.path.exists(FILE_NAME):
        return []

    try:
        with open(FILE_NAME, "r") as file:
            return json.load(file)
    except:
        return []


# ==========================================
# Save Farms
# ==========================================

def save_farms(farms):

    with open(FILE_NAME, "w") as file:
        json.dump(farms, file, indent=4)


# ==========================================
# Generate Farm ID
# ==========================================

def generate_farm_id():

    farms = load_farms()

    if len(farms) == 0:
        return "FM001"

    last_id = farms[-1]["farm_id"]

    number = int(last_id[2:]) + 1

    return f"FM{number:03d}"


# ==========================================
# Add Farm
# ==========================================

def add_farm():

    print(Fore.CYAN + "\n========== ADD FARM ==========\n")

    farms = load_farms()

    farm = {

        "farm_id": generate_farm_id(),
        "farmer_id": input("Farmer ID        : "),
        "farm_name": input("Farm Name        : "),
        "village": input("Village          : "),
        "district": input("District         : "),
        "state": input("State            : "),
        "area": input("Land Area(Acre)  : "),
        "soil_type": input("Soil Type        : "),
        "water_source": input("Water Source     : ")

    }

    farms.append(farm)

    save_farms(farms)

    print(Fore.GREEN + "\nFarm Added Successfully!")
    print(Fore.YELLOW + f"Farm ID : {farm['farm_id']}")


# ==========================================
# View Farms
# ==========================================

def view_farms():

    farms = load_farms()

    print(Fore.CYAN + "\n========== ALL FARMS ==========\n")

    if len(farms) == 0:
        print(Fore.RED + "No Farm Records Found!")
        return

    print("-" * 120)

    print(
        f"{'ID':<8}"
        f"{'Farmer':<10}"
        f"{'Farm Name':<20}"
        f"{'Village':<15}"
        f"{'Area':<10}"
        f"{'Soil':<15}"
        f"{'Water'}"
    )

    print("-" * 120)

    for farm in farms:

        print(
            f"{farm['farm_id']:<8}"
            f"{farm['farmer_id']:<10}"
            f"{farm['farm_name']:<20}"
            f"{farm['village']:<15}"
            f"{farm['area']:<10}"
            f"{farm['soil_type']:<15}"
            f"{farm['water_source']}"
        )

    print("-" * 120)


# ==========================================
# Search Farm
# ==========================================

def search_farm():

    farm_id = input("\nEnter Farm ID : ")

    farms = load_farms()

    for farm in farms:

        if farm["farm_id"] == farm_id:

            print("\nFarm Found\n")

            for key, value in farm.items():
                print(f"{key} : {value}")

            return

    print(Fore.RED + "\nFarm Not Found!")


# ==========================================
# Update Farm
# ==========================================

def update_farm():

    farm_id = input("\nEnter Farm ID : ")

    farms = load_farms()

    for farm in farms:

        if farm["farm_id"] == farm_id:

            farm["farm_name"] = input("New Farm Name : ")
            farm["area"] = input("New Area : ")

            save_farms(farms)

            print(Fore.GREEN + "\nFarm Updated Successfully!")

            return

    print(Fore.RED + "\nFarm Not Found!")


# ==========================================
# Delete Farm
# ==========================================

def delete_farm():

    farm_id = input("\nEnter Farm ID : ")

    farms = load_farms()

    for farm in farms:

        if farm["farm_id"] == farm_id:

            farms.remove(farm)

            save_farms(farms)

            print(Fore.GREEN + "\nFarm Deleted Successfully!")

            return

    print(Fore.RED + "\nFarm Not Found!")


# ==========================================
# Farm Management Menu
# ==========================================

def farm_management():

    while True:

        print(Fore.GREEN + "\n====================================")
        print(Fore.CYAN + "         FARM MANAGEMENT")
        print(Fore.GREEN + "====================================")

        print("1. Add Farm")
        print("2. View Farms")
        print("3. Search Farm")
        print("4. Update Farm")
        print("5. Delete Farm")
        print("6. Back")

        choice = input("\nEnter Your Choice : ")

        if choice == "1":
            add_farm()

        elif choice == "2":
            view_farms()

        elif choice == "3":
            search_farm()

        elif choice == "4":
            update_farm()

        elif choice == "5":
            delete_farm()

        elif choice == "6":
            break

        else:
            print(Fore.RED + "\nInvalid Choice!")