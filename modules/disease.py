import json
import os
import requests
from datetime import datetime
from colorama import Fore, Style
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_KEY = os.getenv("PLANTNET_API_KEY")

API_URL = "https://my-api.plantnet.org/v2/diseases/identify"

FILE_NAME = "database/disease.json"


# ============================================================
# LOAD DISEASE RECORDS
# ============================================================

def load_diseases():

    if not os.path.exists(FILE_NAME):
        return []

    try:
        with open(FILE_NAME, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return []


# ============================================================
# SAVE DISEASE RECORDS
# ============================================================

def save_diseases(data):

    os.makedirs("database", exist_ok=True)

    with open(FILE_NAME, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


# ============================================================
# GENERATE DISEASE ID
# ============================================================

def generate_disease_id():

    data = load_diseases()

    if not data:
        return "D001"

    last_id = data[-1].get("disease_id", "D000")

    try:
        number = int(last_id[1:]) + 1
    except ValueError:
        number = len(data) + 1

    return f"D{number:03d}"


# ============================================================
# CHECK API KEY
# ============================================================

def check_api_key():

    if not API_KEY:

        print(
            Fore.RED
            + "\nPl@ntNet API Key not found!"
            + Style.RESET_ALL
        )

        print(
            Fore.YELLOW
            + "Please add PLANTNET_API_KEY in your .env file."
            + Style.RESET_ALL
        )

        return False

    return True


# ============================================================
# DISEASE DETECTION
# ============================================================

def detect_disease():

    print(
        Fore.CYAN
        + "\n=============================================="
    )

    print("          AI PLANT DISEASE DETECTION")

    print(
        "=============================================="
        + Style.RESET_ALL
    )

    if not check_api_key():
        return

    image_path = input(
        Fore.YELLOW
        + "\nEnter Plant Leaf Image Path : "
        + Style.RESET_ALL
    ).strip()

    # Remove quotes if user pastes path with quotes
    image_path = image_path.strip('"').strip("'")

    if not os.path.exists(image_path):

        print(
            Fore.RED
            + "\nImage file not found!"
            + Style.RESET_ALL
        )

        return

    # Check image extension
    allowed_extensions = [".jpg", ".jpeg", ".png"]

    extension = os.path.splitext(image_path)[1].lower()

    if extension not in allowed_extensions:

        print(
            Fore.RED
            + "\nOnly JPG, JPEG and PNG images are supported."
            + Style.RESET_ALL
        )

        return

    print(
        Fore.CYAN
        + "\nAnalyzing plant image..."
        + Style.RESET_ALL
    )

    try:

        with open(image_path, "rb") as image_file:

            files = {
                "images": (
                    os.path.basename(image_path),
                    image_file,
                    "image/jpeg"
                    if extension in [".jpg", ".jpeg"]
                    else "image/png"
                )
            }

            data = {
                "organs": "leaf"
            }

            params = {
                "api-key": API_KEY,
                "lang": "en",
                "nb-results": 5,
                "include-related-images": "false"
            }

            response = requests.post(
                API_URL,
                params=params,
                files=files,
                data=data,
                timeout=60
            )

        # ====================================================
        # API RESPONSE CHECK
        # ====================================================

        if response.status_code != 200:

            print(
                Fore.RED
                + f"\nAPI Error: {response.status_code}"
                + Style.RESET_ALL
            )

            try:
                print(response.json())
            except ValueError:
                print(response.text)

            return

        result = response.json()

        results = result.get("results", [])

        if not results:

            print(
                Fore.RED
                + "\nNo disease could be identified."
                + Style.RESET_ALL
            )

            return

        # ====================================================
        # BEST RESULT
        # ====================================================

        best_result = results[0]

        disease_name = best_result.get(
            "description",
            "Unknown Disease"
        )

        disease_code = best_result.get(
            "name",
            "N/A"
        )

        score = best_result.get(
            "score",
            0
        )

        confidence = score * 100

        # ====================================================
        # DISPLAY RESULT
        # ====================================================

        print(
            Fore.GREEN
            + "\n=============================================="
        )

        print("              DISEASE DETECTED")

        print(
            "=============================================="
            + Style.RESET_ALL
        )

        print(
            Fore.YELLOW
            + f"Disease       : "
            + Fore.WHITE
            + f"{disease_name}"
        )

        print(
            Fore.YELLOW
            + f"EPPO Code     : "
            + Fore.WHITE
            + f"{disease_code}"
        )

        print(
            Fore.YELLOW
            + f"Confidence    : "
            + Fore.WHITE
            + f"{confidence:.2f}%"
        )

        print(
            Fore.YELLOW
            + f"AI Version    : "
            + Fore.WHITE
            + f"{result.get('version', 'N/A')}"
        )

        print(
            Fore.YELLOW
            + f"Remaining API: "
            + Fore.WHITE
            + f"{result.get('remainingIdentificationRequests', 'N/A')}"
        )

        # ====================================================
        # TOP RESULTS
        # ====================================================

        print(
            Fore.CYAN
            + "\n--------------- TOP RESULTS ----------------"
            + Style.RESET_ALL
        )

        for index, item in enumerate(results, start=1):

            name = item.get(
                "description",
                "Unknown"
            )

            item_score = item.get(
                "score",
                0
            ) * 100

            print(
                f"{index}. {name:<45} "
                f"{item_score:.2f}%"
            )

        # ====================================================
        # SAVE RESULT
        # ====================================================

        disease_records = load_diseases()

        record = {

            "disease_id": generate_disease_id(),

            "image": os.path.basename(image_path),

            "disease_name": disease_name,

            "eppo_code": disease_code,

            "confidence": round(confidence, 2),

            "ai_version": result.get(
                "version",
                "N/A"
            ),

            "date": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

        disease_records.append(record)

        save_diseases(disease_records)

        print(
            Fore.GREEN
            + "\nDisease Detection Record Saved Successfully!"
            + Style.RESET_ALL
        )

    except requests.exceptions.Timeout:

        print(
            Fore.RED
            + "\nAPI request timed out."
            + Style.RESET_ALL
        )

    except requests.exceptions.ConnectionError:

        print(
            Fore.RED
            + "\nInternet connection error."
            + Style.RESET_ALL
        )

    except Exception as e:

        print(
            Fore.RED
            + f"\nError: {e}"
            + Style.RESET_ALL
        )


# ============================================================
# VIEW DISEASE RECORDS
# ============================================================

def view_disease_records():

    records = load_diseases()

    print(
        Fore.CYAN
        + "\n=============================================="
    )

    print("             DISEASE RECORDS")

    print(
        "=============================================="
        + Style.RESET_ALL
    )

    if not records:

        print(
            Fore.RED
            + "\nNo disease records found."
            + Style.RESET_ALL
        )

        return

    print(
        "\n"
        + "-" * 110
    )

    print(
        f"{'ID':<8}"
        f"{'Disease':<35}"
        f"{'EPPO':<12}"
        f"{'Confidence':<15}"
        f"{'Date'}"
    )

    print("-" * 110)

    for record in records:

        print(
            f"{record.get('disease_id', 'N/A'):<8}"
            f"{record.get('disease_name', 'Unknown')[:33]:<35}"
            f"{record.get('eppo_code', 'N/A'):<12}"
            f"{str(record.get('confidence', 0)) + '%':<15}"
            f"{record.get('date', 'N/A')}"
        )

    print("-" * 110)


# ============================================================
# SEARCH DISEASE RECORD
# ============================================================

def search_disease():

    disease_id = input(
        "\nEnter Disease ID : "
    ).strip()

    records = load_diseases()

    for record in records:

        if record.get("disease_id") == disease_id:

            print(
                Fore.GREEN
                + "\nDisease Record Found!"
                + Style.RESET_ALL
            )

            print("\n--------------------------------")

            for key, value in record.items():

                print(
                    f"{key.replace('_', ' ').title()} : {value}"
                )

            print("--------------------------------")

            return

    print(
        Fore.RED
        + "\nDisease Record Not Found!"
        + Style.RESET_ALL
    )


# ============================================================
# DELETE DISEASE RECORD
# ============================================================

def delete_disease():

    disease_id = input(
        "\nEnter Disease ID : "
    ).strip()

    records = load_diseases()

    for record in records:

        if record.get("disease_id") == disease_id:

            records.remove(record)

            save_diseases(records)

            print(
                Fore.GREEN
                + "\nDisease Record Deleted Successfully!"
                + Style.RESET_ALL
            )

            return

    print(
        Fore.RED
        + "\nDisease Record Not Found!"
        + Style.RESET_ALL
    )


# ============================================================
# DISEASE MANAGEMENT MENU
# ============================================================

def disease_management():

    while True:

        print(
            Fore.GREEN
            + "\n=============================================="
        )

        print(
            Fore.CYAN
            + "             DISEASE MANAGEMENT"
        )

        print(
            Fore.GREEN
            + "=============================================="
        )

        print(
            Fore.WHITE
            + "1. AI Disease Detection"
        )

        print("2. View Disease Records")

        print("3. Search Disease Record")

        print("4. Delete Disease Record")

        print("5. Back")

        print(
            Fore.GREEN
            + "=============================================="
            + Style.RESET_ALL
        )

        choice = input(
            "\nEnter Your Choice : "
        ).strip()

        if choice == "1":

            detect_disease()

        elif choice == "2":

            view_disease_records()

        elif choice == "3":

            search_disease()

        elif choice == "4":

            delete_disease()

        elif choice == "5":

            break

        else:

            print(
                Fore.RED
                + "\nInvalid Choice!"
                + Style.RESET_ALL
            )