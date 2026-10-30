import json
import os
import sys
from colorama import Fore


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

FILE_NAME = "database/fertilizer.json"


# ==========================================
# Load Fertilizer Data
# ==========================================

def load_fertilizers():

    if not os.path.exists(FILE_NAME):
        return []

    try:

        with open(FILE_NAME, "r", encoding="utf-8") as file:
            return json.load(file)

    except:

        return []


# ==========================================
# Save Fertilizer Data
# ==========================================

def save_fertilizers(data):

    os.makedirs("database", exist_ok=True)

    with open(FILE_NAME, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


# ==========================================
# Generate Fertilizer ID
# ==========================================

def generate_fertilizer_id():

    fertilizers = load_fertilizers()

    if len(fertilizers) == 0:
        return "F001"

    last_id = fertilizers[-1]["fertilizer_id"]

    number = int(last_id[1:]) + 1

    return f"F{number:03d}"


# ==========================================
# Add Fertilizer
# ==========================================

def add_fertilizer():

    print(
        Fore.CYAN +
        "\n========== ADD FERTILIZER ==========\n"
    )

    fertilizers = load_fertilizers()

    fertilizer_id = generate_fertilizer_id()


    # Fertilizer Name
    while True:

        name = input(
            "Fertilizer Name      : "
        ).strip()

        if name != "":
            break

        print(
            Fore.RED +
            "Fertilizer name cannot be empty!"
        )


    # Fertilizer Type
    while True:

        fertilizer_type = input(
            "Fertilizer Type      : "
        ).strip()

        if fertilizer_type != "":
            break

        print(
            Fore.RED +
            "Fertilizer type cannot be empty!"
        )


    # Crop
    while True:

        crop = input(
            "Suitable Crop        : "
        ).strip()

        if crop != "":
            break

        print(
            Fore.RED +
            "Crop name cannot be empty!"
        )


    # Nutrient
    while True:

        nutrient = input(
            "Main Nutrient (N/P/K): "
        ).strip().upper()

        if nutrient in ["N", "P", "K"]:

            break

        print(
            Fore.RED +
            "Enter only N, P or K!"
        )


    # Quantity
    while True:

        quantity = input(
            "Quantity (kg/acre)    : "
        ).strip()

        try:

            quantity_value = float(quantity)

            if quantity_value > 0:
                break

        except:
            pass

        print(
            Fore.RED +
            "Enter a valid quantity!"
        )


    # Application Schedule
    while True:

        schedule = input(
            "Application Schedule : "
        ).strip()

        if schedule != "":
            break

        print(
            Fore.RED +
            "Application schedule cannot be empty!"
        )


    # ==========================================
    # Create Fertilizer Record
    # ==========================================

    fertilizer = {

        "fertilizer_id": fertilizer_id,
        "name": name,
        "type": fertilizer_type,
        "crop": crop,
        "nutrient": nutrient,
        "quantity": quantity_value,
        "schedule": schedule

    }


    fertilizers.append(fertilizer)

    save_fertilizers(fertilizers)


    print(
        Fore.GREEN +
        "\nFertilizer Added Successfully!"
    )

    print(
        Fore.YELLOW +
        f"Fertilizer ID : {fertilizer_id}"
    )


# ==========================================
# View Fertilizers
# ==========================================

def view_fertilizers():

    fertilizers = load_fertilizers()

    print(
        Fore.CYAN +
        "\n========== FERTILIZER RECORDS ==========\n"
    )

    if len(fertilizers) == 0:

        print(
            Fore.RED +
            "No Fertilizer Records Found!"
        )

        return


    print("-" * 120)

    print(
        f"{'ID':<8}"
        f"{'Name':<20}"
        f"{'Type':<15}"
        f"{'Crop':<15}"
        f"{'Nutrient':<10}"
        f"{'Quantity':<15}"
        f"{'Schedule'}"
    )

    print("-" * 120)


    for fertilizer in fertilizers:

        print(
            f"{fertilizer['fertilizer_id']:<8}"
            f"{fertilizer['name']:<20}"
            f"{fertilizer['type']:<15}"
            f"{fertilizer['crop']:<15}"
            f"{fertilizer['nutrient']:<10}"
            f"{fertilizer['quantity']:<15}"
            f"{fertilizer['schedule']}"
        )


    print("-" * 120)


# ==========================================
# Search Fertilizer
# ==========================================

def search_fertilizer():

    print(
        Fore.CYAN +
        "\n========== SEARCH FERTILIZER ==========\n"
    )

    fertilizer_id = input(
        "Enter Fertilizer ID : "
    ).strip().upper()


    fertilizers = load_fertilizers()


    for fertilizer in fertilizers:

        if fertilizer["fertilizer_id"] == fertilizer_id:

            print(
                Fore.GREEN +
                "\nFertilizer Found!\n"
            )

            print(
                f"Fertilizer ID        : "
                f"{fertilizer['fertilizer_id']}"
            )

            print(
                f"Name                 : "
                f"{fertilizer['name']}"
            )

            print(
                f"Type                 : "
                f"{fertilizer['type']}"
            )

            print(
                f"Suitable Crop        : "
                f"{fertilizer['crop']}"
            )

            print(
                f"Main Nutrient        : "
                f"{fertilizer['nutrient']}"
            )

            print(
                f"Quantity             : "
                f"{fertilizer['quantity']} kg/acre"
            )

            print(
                f"Application Schedule : "
                f"{fertilizer['schedule']}"
            )

            return


    print(
        Fore.RED +
        "\nFertilizer Not Found!"
    )


# ==========================================
# Delete Fertilizer
# ==========================================

def delete_fertilizer():

    print(
        Fore.CYAN +
        "\n========== DELETE FERTILIZER ==========\n"
    )

    fertilizer_id = input(
        "Enter Fertilizer ID : "
    ).strip().upper()


    fertilizers = load_fertilizers()


    for fertilizer in fertilizers:

        if fertilizer["fertilizer_id"] == fertilizer_id:

            fertilizers.remove(fertilizer)

            save_fertilizers(fertilizers)

            print(
                Fore.GREEN +
                "\nFertilizer Deleted Successfully!"
            )

            return


    print(
        Fore.RED +
        "\nFertilizer Not Found!"
    )


# ==========================================
# Fertilizer Recommendation
# ==========================================

def fertilizer_recommendation():

    print(
        Fore.CYAN +
        "\n========== FERTILIZER RECOMMENDATION ==========\n"
    )


    # Crop
    crop = input(
        "Enter Crop Name : "
    ).strip().lower()


    # Nitrogen
    while True:

        nitrogen = input(
            "Nitrogen Level (Low/Medium/High) : "
        ).strip().lower()

        if nitrogen in ["low", "medium", "high"]:
            break

        print(
            Fore.RED +
            "Enter Low, Medium or High!"
        )


    # Phosphorus
    while True:

        phosphorus = input(
            "Phosphorus Level (Low/Medium/High) : "
        ).strip().lower()

        if phosphorus in ["low", "medium", "high"]:
            break

        print(
            Fore.RED +
            "Enter Low, Medium or High!"
        )


    # Potassium
    while True:

        potassium = input(
            "Potassium Level (Low/Medium/High) : "
        ).strip().lower()

        if potassium in ["low", "medium", "high"]:
            break

        print(
            Fore.RED +
            "Enter Low, Medium or High!"
        )


    print(
        Fore.YELLOW +
        "\nAnalyzing Soil Nutrient Levels..."
    )


    # ==========================================
    # Recommendation Logic
    # ==========================================

    if nitrogen == "low":

        fertilizer = "Urea"

        quantity = "45-50 kg/acre"

        reason = (
            "Nitrogen level is low. "
            "Urea can help improve nitrogen availability."
        )


    elif phosphorus == "low":

        fertilizer = "DAP"

        quantity = "40-50 kg/acre"

        reason = (
            "Phosphorus level is low. "
            "DAP can help improve phosphorus availability."
        )


    elif potassium == "low":

        fertilizer = "MOP"

        quantity = "25-30 kg/acre"

        reason = (
            "Potassium level is low. "
            "MOP can help improve potassium availability."
        )


    else:

        fertilizer = "Organic Compost"

        quantity = "2-3 tons/acre"

        reason = (
            "Major NPK levels are not low. "
            "Organic compost can help maintain soil health."
        )


    # ==========================================
    # Display Recommendation
    # ==========================================

    print(
        Fore.GREEN +
        "\n========== RECOMMENDATION =========="
    )

    print(
        Fore.YELLOW +
        f"Crop                  : {crop.capitalize()}"
    )

    print(
        Fore.YELLOW +
        f"Recommended Fertilizer: {fertilizer}"
    )

    print(
        Fore.YELLOW +
        f"Recommended Quantity  : {quantity}"
    )

    print(
        Fore.YELLOW +
        f"Reason                : {reason}"
    )

    print(
        Fore.GREEN +
        "===================================="
    )


# ==========================================
# Fertilizer Management Menu
# ==========================================

def fertilizer_management():

    while True:

        print(
            Fore.GREEN +
            "\n===================================="
        )

        print(
            Fore.CYAN +
            "      FERTILIZER MANAGEMENT"
        )

        print(
            Fore.GREEN +
            "===================================="
        )

        print(
            Fore.WHITE +
            "1. Add Fertilizer"
        )

        print(
            Fore.WHITE +
            "2. View Fertilizers"
        )

        print(
            Fore.WHITE +
            "3. Search Fertilizer"
        )

        print(
            Fore.WHITE +
            "4. Delete Fertilizer"
        )

        print(
            Fore.WHITE +
            "5. Fertilizer Recommendation"
        )

        print(
            Fore.WHITE +
            "6. Back"
        )


        choice = input(
            "\nEnter Your Choice : "
        ).strip()


        if choice == "1":

            add_fertilizer()


        elif choice == "2":

            view_fertilizers()


        elif choice == "3":

            search_fertilizer()


        elif choice == "4":

            delete_fertilizer()


        elif choice == "5":

            fertilizer_recommendation()


        elif choice == "6":

            break


        else:

            print(
                Fore.RED +
                "\nInvalid Choice!"
            )