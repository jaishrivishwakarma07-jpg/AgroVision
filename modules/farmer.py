import json
import os
from colorama import Fore

FILE_NAME = "database/farmers.json"


# ==========================================
# Load Farmers
# ==========================================

def load_farmers():

    if not os.path.exists(FILE_NAME):
        return []

    try:
        with open(FILE_NAME, "r") as file:
            return json.load(file)
    except:
        return []


# ==========================================
# Save Farmers
# ==========================================

def save_farmers(farmers):

    with open(FILE_NAME, "w") as file:
        json.dump(farmers, file, indent=4)


# ==========================================
# Generate Farmer ID
# ==========================================

def generate_farmer_id():

    farmers = load_farmers()

    if len(farmers) == 0:
        return "F001"

    last_id = farmers[-1]["farmer_id"]

    number = int(last_id[1:]) + 1

    return f"F{number:03d}"


# ==========================================
# Add Farmer
# ==========================================

def add_farmer():

    print(Fore.CYAN + "\n========== ADD FARMER ==========\n")

    farmers = load_farmers()

    farmer_id = generate_farmer_id()

    # Farmer Name
    while True:
        name = input("Farmer Name      : ").strip()

        if name != "":
            break

        print(Fore.RED + "Name cannot be empty!")

    # Age
    while True:

        age = input("Age              : ")

        if age.isdigit() and 18 <= int(age) <= 100:
            break

        print(Fore.RED + "Enter a valid age (18-100).")

    # Gender
    while True:

        gender = input("Gender (Male/Female): ").strip().capitalize()

        if gender in ["Male", "Female"]:
            break

        print(Fore.RED + "Enter Male or Female.")

    # Mobile Number
    while True:

        mobile = input("Mobile Number    : ")

        if not mobile.isdigit() or len(mobile) != 10:
            print(Fore.RED + "Mobile number must contain exactly 10 digits.")
            continue

        duplicate = False

        for farmer in farmers:
            if farmer["mobile"] == mobile:
                duplicate = True
                break

        if duplicate:
            print(Fore.RED + "Mobile number already exists!")
            continue

        break
    # Village
    while True:

        village = input("Village          : ").strip()

        if village != "":
            break

        print(Fore.RED + "Village cannot be empty.")

    # District
    while True:

        district = input("District         : ").strip()

        if district != "":
            break

        print(Fore.RED + "District cannot be empty.")

    # State
    while True:

        state = input("State            : ").strip()

        if state != "":
            break

        print(Fore.RED + "State cannot be empty.")

    # Land Area
    while True:

        land = input("Land Area(Acre)  : ")

        try:

            land = float(land)

            if land > 0:
                break

        except:
            pass

        print(Fore.RED + "Enter valid land area.")

    farmer = {

        "farmer_id": farmer_id,
        "name": name,
        "age": age,
        "gender": gender,
        "mobile": mobile,
        "village": village,
        "district": district,
        "state": state,
        "land": land

    }

    farmers.append(farmer)

    save_farmers(farmers)

    print(Fore.GREEN + "\nFarmer Added Successfully!")
    print(Fore.YELLOW + f"Farmer ID : {farmer_id}")

# ==========================================
# View Farmers
# ==========================================

def view_farmers():

    farmers = load_farmers()

    print(Fore.CYAN + "\n========== ALL FARMERS ==========\n")

    if len(farmers) == 0:
        print(Fore.RED + "No Farmer Records Found!")
        return

    print("-" * 110)

    print(
        f"{'ID':<8}"
        f"{'Name':<20}"
        f"{'Age':<8}"
        f"{'Gender':<10}"
        f"{'Mobile':<15}"
        f"{'Village':<15}"
        f"{'Land'}"
    )

    print("-" * 110)

    for farmer in farmers:

        print(
            f"{farmer['farmer_id']:<8}"
            f"{farmer['name']:<20}"
            f"{farmer['age']:<8}"
            f"{farmer['gender']:<10}"
            f"{farmer['mobile']:<15}"
            f"{farmer['village']:<15}"
            f"{farmer['land']}"
        )

    print("-" * 110)


# ==========================================
# Search Farmer
# ==========================================

def search_farmer():

    print(Fore.CYAN + "\n========== SEARCH FARMER ==========\n")

    farmer_id = input("Enter Farmer ID : ")

    farmers = load_farmers()

    for farmer in farmers:

        if farmer["farmer_id"] == farmer_id:

            print("\nFarmer Found\n")

            for key, value in farmer.items():
                print(f"{key.capitalize()} : {value}")

            return

    print(Fore.RED + "\nFarmer Not Found!")


# ==========================================
# Update Farmer
# ==========================================

def update_farmer():

    print(Fore.CYAN + "\n========== UPDATE FARMER ==========\n")

    farmer_id = input("Enter Farmer ID : ")

    farmers = load_farmers()

    for farmer in farmers:

        if farmer["farmer_id"] == farmer_id:

            farmer["name"] = input("New Name : ")
            farmer["age"] = input("New Age : ")
            farmer["mobile"] = input("New Mobile : ")

            save_farmers(farmers)

            print(Fore.GREEN + "\nFarmer Updated Successfully!")

            return

    print(Fore.RED + "\nFarmer Not Found!")


# ==========================================
# Delete Farmer
# ==========================================

def delete_farmer():

    print(Fore.CYAN + "\n========== DELETE FARMER ==========\n")

    farmer_id = input("Enter Farmer ID : ")

    farmers = load_farmers()

    for farmer in farmers:

        if farmer["farmer_id"] == farmer_id:

            farmers.remove(farmer)

            save_farmers(farmers)

            print(Fore.GREEN + "\nFarmer Deleted Successfully!")

            return

    print(Fore.RED + "\nFarmer Not Found!")


# ==========================================
# Farmer Management Menu
# ==========================================

def farmer_management():

    while True:

        print(Fore.GREEN + "\n====================================")
        print(Fore.CYAN + "       FARMER MANAGEMENT")
        print(Fore.GREEN + "====================================")

        print("1. Add Farmer")
        print("2. View Farmers")
        print("3. Search Farmer")
        print("4. Update Farmer")
        print("5. Delete Farmer")
        print("6. Back")

        choice = input("\nEnter Your Choice : ")

        if choice == "1":
            add_farmer()

        elif choice == "2":
            view_farmers()

        elif choice == "3":
            search_farmer()

        elif choice == "4":
            update_farmer()

        elif choice == "5":
            delete_farmer()

        elif choice == "6":
            break

        else:
            print(Fore.RED + "\nInvalid Choice!")
    

