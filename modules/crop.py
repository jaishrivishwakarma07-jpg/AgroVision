import json
import os
from colorama import Fore

FILE_NAME = "database/crops.json"


# ==========================================
# Load Crops
# ==========================================

def load_crops():

    if not os.path.exists(FILE_NAME):
        return []

    try:
        with open(FILE_NAME, "r") as file:
            return json.load(file)
    except:
        return []


# ==========================================
# Save Crops
# ==========================================

def save_crops(crops):

    with open(FILE_NAME, "w") as file:
        json.dump(crops, file, indent=4)


# ==========================================
# Generate Crop ID
# ==========================================

def generate_crop_id():

    crops = load_crops()

    if len(crops) == 0:
        return "C001"

    last_id = crops[-1]["crop_id"]

    number = int(last_id[1:]) + 1

    return f"C{number:03d}"


# ==========================================
# Add Crop
# ==========================================

def add_crop():

    print(Fore.CYAN + "\n========== ADD CROP ==========\n")

    crops = load_crops()

    crop = {

        "crop_id": generate_crop_id(),
        "farm_id": input("Farm ID              : "),
        "crop_name": input("Crop Name            : "),
        "category": input("Category             : "),
        "season": input("Season               : "),
        "sowing_date": input("Sowing Date          : "),
        "harvest_date": input("Harvest Date         : "),
        "stage": input("Current Stage        : "),
        "status": input("Status               : ")

    }

    crops.append(crop)

    save_crops(crops)

    print(Fore.GREEN + "\nCrop Added Successfully!")
    print(Fore.YELLOW + f"Crop ID : {crop['crop_id']}")


# ==========================================
# View Crops
# ==========================================

def view_crops():

    crops = load_crops()

    print(Fore.CYAN + "\n========== ALL CROPS ==========\n")

    if len(crops) == 0:
        print(Fore.RED + "No Crop Records Found!")
        return

    print("-"*120)

    print(
        f"{'ID':<8}"
        f"{'Farm':<10}"
        f"{'Crop':<20}"
        f"{'Season':<12}"
        f"{'Stage':<18}"
        f"{'Status'}"
    )

    print("-"*120)

    for crop in crops:

        print(
            f"{crop['crop_id']:<8}"
            f"{crop['farm_id']:<10}"
            f"{crop['crop_name']:<20}"
            f"{crop['season']:<12}"
            f"{crop['stage']:<18}"
            f"{crop['status']}"
        )

    print("-"*120)


# ==========================================
# Search Crop
# ==========================================

def search_crop():

    crop_id = input("\nEnter Crop ID : ")

    crops = load_crops()

    for crop in crops:

        if crop["crop_id"] == crop_id:

            print("\nCrop Found\n")

            for key, value in crop.items():
                print(f"{key} : {value}")

            return

    print(Fore.RED + "\nCrop Not Found!")


# ==========================================
# Update Crop
# ==========================================

def update_crop():

    crop_id = input("\nEnter Crop ID : ")

    crops = load_crops()

    for crop in crops:

        if crop["crop_id"] == crop_id:

            crop["crop_name"] = input("New Crop Name : ")
            crop["stage"] = input("Current Stage : ")
            crop["status"] = input("Status : ")

            save_crops(crops)

            print(Fore.GREEN + "\nCrop Updated Successfully!")

            return

    print(Fore.RED + "\nCrop Not Found!")


# ==========================================
# Delete Crop
# ==========================================

def delete_crop():

    crop_id = input("\nEnter Crop ID : ")

    crops = load_crops()

    for crop in crops:

        if crop["crop_id"] == crop_id:

            crops.remove(crop)

            save_crops(crops)

            print(Fore.GREEN + "\nCrop Deleted Successfully!")

            return

    print(Fore.RED + "\nCrop Not Found!")


# ==========================================
# Crop History
# ==========================================

def crop_history():

    print(Fore.CYAN + "\nCrop History Feature Coming Soon...")


# ==========================================
# Harvest Details
# ==========================================

def harvest_details():

    print(Fore.CYAN + "\nHarvest Details Feature Coming Soon...")


# ==========================================
# Crop Management Menu
# ==========================================

def crop_management():

    while True:

        print(Fore.GREEN + "\n====================================")
        print(Fore.CYAN + "         CROP MANAGEMENT")
        print(Fore.GREEN + "====================================")

        print("1. Add Crop")
        print("2. View Crops")
        print("3. Search Crop")
        print("4. Update Crop")
        print("5. Delete Crop")
        print("6. Crop History")
        print("7. Harvest Details")
        print("8. Back")

        choice = input("\nEnter Your Choice : ")

        if choice == "1":
            add_crop()

        elif choice == "2":
            view_crops()

        elif choice == "3":
            search_crop()

        elif choice == "4":
            update_crop()

        elif choice == "5":
            delete_crop()

        elif choice == "6":
            crop_history()

        elif choice == "7":
            harvest_details()

        elif choice == "8":
            break

        else:
            print(Fore.RED + "\nInvalid Choice!")