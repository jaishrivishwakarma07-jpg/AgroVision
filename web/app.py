import sys
import os
import json
import base64
from datetime import datetime
from pathlib import Path

import requests

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    redirect,
    url_for,
    session,
    flash,
)

from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Project root ko Python path mein add karo
BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ab project ke modules import ho sakte hain
from modules import crop, farmer


# ============================================================
# AGROVISION
# AI-Powered Smart Agriculture Management System
# Plant Identification + Disease Detection + Open-Meteo
# ============================================================

# ------------------------------------------------------------
# BASE PATHS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
UPLOAD_FOLDER = WEB_DIR / "uploads"
DATABASE_DIR = BASE_DIR / "database"

# Add project root to Python import path
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Import plant requirements function
from AI.plant_requirements import get_plant_requirements

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ------------------------------------------------------------

ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)


PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY", "").strip()
PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY", "").strip()
PERENUAL_API_KEY = os.getenv("PERENUAL_API_KEY", "").strip()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()


# ------------------------------------------------------------
# API URLS
# ------------------------------------------------------------

PLANTNET_SPECIES_API_URL = (
    "https://my-api.plantnet.org/v2/identify/all"
)

PLANTNET_DISEASE_API_URL = (
    "https://my-api.plantnet.org/v2/diseases/identify"
)

PLANT_ID_API_URL = (
    "https://api.plant.id/v3/identification"
)

PERENUAL_SPECIES_LIST_URL = (
    "https://www.perenual.com/api/v2/species-list"
)

PERENUAL_DETAILS_URL = (
    "https://www.perenual.com/api/v2/species/details"
)

OPEN_METEO_API_URL = (
    "https://api.open-meteo.com/v1/forecast"
)


# ------------------------------------------------------------
# SETTINGS
# ------------------------------------------------------------

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

MAX_CONTENT_LENGTH = 50 * 1024 * 1024

SPECIES_HIGH_CONFIDENCE = 70.0
SPECIES_MEDIUM_CONFIDENCE = 40.0

DISEASE_ACCEPTANCE_THRESHOLD = 40.0


# ------------------------------------------------------------
# FLASK APP
# ------------------------------------------------------------

app = Flask(
    __name__,
    template_folder=str(WEB_DIR / "templates")
)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
# Browser login session configuration
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "agrovision-development-key-change-before-deployment"
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ============================================================
# JSON DATABASE HELPERS
# ============================================================

def load_json(filename, default=None):
    """
    Load JSON file safely.
    """

    if default is None:
        default = []

    file_path = DATABASE_DIR / filename

    try:
        if not file_path.exists():
            return default

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except Exception:
        return default


def save_json(filename, data):
    """
    Save JSON data safely.
    """

    file_path = DATABASE_DIR / filename

    try:
        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as error:
        print(f"JSON save error: {error}")
        return False


# ============================================================
# GENERAL HELPERS
# ============================================================

def safe_percentage(value):
    """
    Convert confidence 0-1 into percentage 0-100.
    """

    try:
        value = float(value)

        if value <= 1:
            value *= 100

        return round(value, 2)

    except Exception:
        return 0.0


def normalize_scientific_name(name):
    """
    Normalize scientific name for comparison.
    """

    if not name:
        return ""

    name = str(name).strip()

    # Remove author information after first two words
    parts = name.split()

    if len(parts) >= 2:
        return (
            parts[0].capitalize()
            + " "
            + parts[1].lower()
        )

    return name


def get_genus(scientific_name):
    """
    Get genus from scientific name.
    """

    if not scientific_name:
        return ""

    return str(scientific_name).split()[0].lower()


def confidence_label(confidence):
    """
    Convert confidence into human-readable label.
    """

    if confidence >= SPECIES_HIGH_CONFIDENCE:
        return "High Confidence"

    if confidence >= SPECIES_MEDIUM_CONFIDENCE:
        return "Medium Confidence"

    return "Low Confidence"


def allowed_file(filename):
    """
    Check uploaded file extension.
    """

    if not filename:
        return False

    extension = filename.rsplit(".", 1)[-1].lower()

    return extension in ALLOWED_EXTENSIONS


def now_string():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# PLANTNET SPECIES IDENTIFICATION
# ============================================================

def detect_with_plantnet_species(image_path):
    """
    Identify plant species using Pl@ntNet.
    """

    if not PLANTNET_API_KEY:
        return {
            "success": False,
            "source": "Pl@ntNet",
            "error": "Pl@ntNet API key is not configured."
        }

    try:

        with open(image_path, "rb") as image_file:

            files = {
                "images": (
                    os.path.basename(image_path),
                    image_file,
                    "image/jpeg"
                )
            }

            data = {
                "organs": "auto"
            }

            params = {
                "api-key": PLANTNET_API_KEY,
                "nb-results": 5,
                "lang": "en"
            }

            response = requests.post(
                PLANTNET_SPECIES_API_URL,
                params=params,
                files=files,
                data=data,
                timeout=60
            )

        if response.status_code != 200:

            return {
                "success": False,
                "source": "Pl@ntNet",
                "error": (
                    f"Pl@ntNet species API error "
                    f"({response.status_code})"
                )
            }

        result = response.json()

        results = result.get("results", [])

        if not results:

            return {
                "success": False,
                "source": "Pl@ntNet",
                "error": "No plant species result returned."
            }

        best = results[0]

        species = best.get("species", {})

        scientific_name = (
            species.get("scientificNameWithoutAuthor")
            or species.get("scientificName")
            or result.get("bestMatch")
            or "Unknown Plant"
        )

        scientific_name = normalize_scientific_name(
            scientific_name
        )

        common_names = species.get(
            "commonNames",
            []
        )

        common_name = ""

        if common_names:
            common_name = common_names[0]

        confidence = safe_percentage(
            best.get("score", 0)
        )

        alternatives = []

        for item in results[1:5]:

            item_species = item.get(
                "species",
                {}
            )

            item_name = (
                item_species.get(
                    "scientificNameWithoutAuthor"
                )
                or item_species.get(
                    "scientificName"
                )
                or "Unknown"
            )

            item_common = ""

            item_common_names = item_species.get(
                "commonNames",
                []
            )

            if item_common_names:
                item_common = item_common_names[0]

            alternatives.append({
                "scientific_name": normalize_scientific_name(
                    item_name
                ),
                "common_name": item_common,
                "confidence": safe_percentage(
                    item.get("score", 0)
                )
            })

        return {
            "success": True,
            "source": "Pl@ntNet",
            "scientific_name": scientific_name,
            "common_name": common_name,
            "confidence": confidence,
            "confidence_label": confidence_label(
                confidence
            ),
            "alternatives": alternatives,
            "raw": result
        }

    except Exception as error:

        return {
            "success": False,
            "source": "Pl@ntNet",
            "error": str(error)
        }


# ============================================================
# PLANT.ID SPECIES IDENTIFICATION
# ============================================================

def detect_with_plant_id(image_path):
    """
    Identify plant species using Plant.id v3.
    """

    if not PLANT_ID_API_KEY:

        return {
            "success": False,
            "source": "Plant.id",
            "error": "Plant.id API key is not configured."
        }

    try:

        with open(
            image_path,
            "rb"
        ) as image_file:

            image_bytes = image_file.read()

        image_base64 = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        headers = {
            "Api-Key": PLANT_ID_API_KEY,
            "Content-Type": "application/json"
        }

        params = {
            "details": (
                "common_names,"
                "url,"
                "description,"
                "taxonomy"
            ),
            "language": "en"
        }

        payload = {
            "images": [
                image_base64
            ]
        }

        response = requests.post(
            PLANT_ID_API_URL,
            headers=headers,
            params=params,
            json=payload,
            timeout=60
        )

        if not (
            200
            <= response.status_code
            < 300
        ):

            return {
                "success": False,
                "source": "Plant.id",
                "error": (
                    f"Plant.id API error "
                    f"({response.status_code})"
                )
            }

        result = response.json()

        classification = (
            result
            .get("result", {})
            .get("classification", [])
        )

        if not classification:

            return {
                "success": False,
                "source": "Plant.id",
                "error": "No plant identification result."
            }

        # Plant.id v3 classification is a list
        best = classification[0]

        name = best.get(
            "name",
            "Unknown Plant"
        )

        confidence = safe_percentage(
            best.get(
                "probability",
                best.get("confidence", 0)
            )
        )

        details = best.get(
            "details",
            {}
        )

        common_names = details.get(
            "common_names",
            []
        )

        common_name = ""

        if common_names:
            common_name = common_names[0]

        description = details.get(
            "description",
            {}
        )

        if isinstance(description, dict):
            description = description.get(
                "value",
                ""
            )

        taxonomy = details.get(
            "taxonomy",
            {}
        )

        alternatives = []

        for item in classification[1:5]:

            item_name = item.get(
                "name",
                "Unknown"
            )

            item_confidence = safe_percentage(
                item.get(
                    "probability",
                    item.get(
                        "confidence",
                        0
                    )
                )
            )

            item_details = item.get(
                "details",
                {}
            )

            item_common_names = item_details.get(
                "common_names",
                []
            )

            item_common = ""

            if item_common_names:
                item_common = item_common_names[0]

            alternatives.append({
                "scientific_name": normalize_scientific_name(
                    item_name
                ),
                "common_name": item_common,
                "confidence": item_confidence
            })

        return {
            "success": True,
            "source": "Plant.id",
            "scientific_name": normalize_scientific_name(
                name
            ),
            "common_name": common_name,
            "confidence": confidence,
            "confidence_label": confidence_label(
                confidence
            ),
            "description": description,
            "taxonomy": taxonomy,
            "alternatives": alternatives,
            "raw": result
        }

    except Exception as error:

        return {
            "success": False,
            "source": "Plant.id",
            "error": str(error)
        }


# ============================================================
# COMPARE BOTH SPECIES RESULTS
# ============================================================

def compare_species_results(
    plantnet_result,
    plantid_result
):
    """
    Compare Pl@ntNet and Plant.id.

    Important:
    Do NOT artificially increase confidence.
    """

    pn_success = plantnet_result.get(
        "success",
        False
    )

    pi_success = plantid_result.get(
        "success",
        False
    )

    if not pn_success and not pi_success:

        return {
            "success": False,
            "scientific_name": "Unknown Plant",
            "common_name": "",
            "confidence": 0.0,
            "status": "Identification Failed",
            "message": (
                "Both AI identification engines "
                "could not identify the plant."
            ),
            "verification": "",
            "source": "No AI result",
            "alternatives": []
        }

    # --------------------------------------------------------
    # Only Pl@ntNet succeeded
    # --------------------------------------------------------

    if pn_success and not pi_success:

        confidence = plantnet_result[
            "confidence"
        ]

        return {
            "success": True,
            "scientific_name": plantnet_result[
                "scientific_name"
            ],
            "common_name": plantnet_result.get(
                "common_name",
                ""
            ),
            "confidence": confidence,
            "confidence_label": confidence_label(
                confidence
            ),
            "status": (
                "Identified by Pl@ntNet"
            ),
            "message": (
                "Plant.id could not provide "
                "a second identification."
            ),
            "verification": (
                "Single-engine identification"
            ),
            "source": "Pl@ntNet",
            "alternatives": plantnet_result.get(
                "alternatives",
                []
            )
        }

    # --------------------------------------------------------
    # Only Plant.id succeeded
    # --------------------------------------------------------

    if pi_success and not pn_success:

        confidence = plantid_result[
            "confidence"
        ]

        return {
            "success": True,
            "scientific_name": plantid_result[
                "scientific_name"
            ],
            "common_name": plantid_result.get(
                "common_name",
                ""
            ),
            "confidence": confidence,
            "confidence_label": confidence_label(
                confidence
            ),
            "status": (
                "Identified by Plant.id"
            ),
            "message": (
                "Pl@ntNet could not provide "
                "a second identification."
            ),
            "verification": (
                "Single-engine identification"
            ),
            "source": "Plant.id",
            "alternatives": plantid_result.get(
                "alternatives",
                []
            )
        }

    # --------------------------------------------------------
    # Both succeeded
    # --------------------------------------------------------

    pn_name = normalize_scientific_name(
        plantnet_result.get(
            "scientific_name",
            ""
        )
    )

    pi_name = normalize_scientific_name(
        plantid_result.get(
            "scientific_name",
            ""
        )
    )

    pn_genus = get_genus(pn_name)
    pi_genus = get_genus(pi_name)

    pn_confidence = plantnet_result.get(
        "confidence",
        0
    )

    pi_confidence = plantid_result.get(
        "confidence",
        0
    )

    # --------------------------------------------------------
    # EXACT SPECIES AGREEMENT
    # --------------------------------------------------------

    if (
        pn_name
        and pi_name
        and pn_name.lower()
        == pi_name.lower()
    ):

        # Use the strongest actual AI confidence.
        # No artificial confidence increase.
        confidence = max(
            pn_confidence,
            pi_confidence
        )

        common_name = (
            plantid_result.get(
                "common_name"
            )
            or plantnet_result.get(
                "common_name"
            )
            or ""
        )

        return {
            "success": True,
            "scientific_name": pn_name,
            "common_name": common_name,
            "confidence": confidence,
            "confidence_label": confidence_label(
                confidence
            ),
            "status": (
                "Verified by both AI engines"
            ),
            "message": (
                "Pl@ntNet and Plant.id "
                "identified the same species."
            ),
            "verification": (
                "Both AI engines agree"
            ),
            "source": (
                "Pl@ntNet + Plant.id"
            ),
            "alternatives": (
                plantnet_result.get(
                    "alternatives",
                    []
                )
            )
        }

    # --------------------------------------------------------
    # SAME GENUS
    # --------------------------------------------------------

    if (
        pn_genus
        and pi_genus
        and pn_genus == pi_genus
    ):

        # Choose the higher-confidence candidate.
        if pn_confidence >= pi_confidence:

            selected = plantnet_result
            other = plantid_result

        else:

            selected = plantid_result
            other = plantnet_result

        confidence = selected.get(
            "confidence",
            0
        )

        alternatives = []

        alternatives.append({
            "scientific_name": other.get(
                "scientific_name",
                "Unknown"
            ),
            "common_name": other.get(
                "common_name",
                ""
            ),
            "confidence": other.get(
                "confidence",
                0
            )
        })

        alternatives.extend(
            selected.get(
                "alternatives",
                []
            )
        )

        return {
            "success": True,
            "scientific_name": selected.get(
                "scientific_name",
                "Unknown Plant"
            ),
            "common_name": selected.get(
                "common_name",
                ""
            ),
            "confidence": confidence,
            "confidence_label": confidence_label(
                confidence
            ),
            "status": (
                "Probable identification"
            ),
            "message": (
                "Both AI engines identified "
                "the same plant genus, but "
                "species-level results differ."
            ),
            "verification": (
                "Genus agreement"
            ),
            "source": (
                selected.get(
                    "source",
                    "AI"
                )
                + " + genus verification"
            ),
            "alternatives": alternatives
        }

    # --------------------------------------------------------
    # STRONG SINGLE ENGINE
    # --------------------------------------------------------

    if (
        pn_confidence >= SPECIES_HIGH_CONFIDENCE
        and pi_confidence
        < SPECIES_MEDIUM_CONFIDENCE
    ):

        return {
            "success": True,
            "scientific_name": pn_name,
            "common_name": plantnet_result.get(
                "common_name",
                ""
            ),
            "confidence": pn_confidence,
            "confidence_label": confidence_label(
                pn_confidence
            ),
            "status": (
                "Identified by Pl@ntNet"
            ),
            "message": (
                "Pl@ntNet produced a strong "
                "species match, while Plant.id "
                "returned a low-confidence result."
            ),
            "verification": (
                "Single-engine strong match"
            ),
            "source": "Pl@ntNet",
            "alternatives": [
                {
                    "scientific_name": pi_name,
                    "common_name": plantid_result.get(
                        "common_name",
                        ""
                    ),
                    "confidence": pi_confidence
                }
            ]
        }

    if (
        pi_confidence >= SPECIES_HIGH_CONFIDENCE
        and pn_confidence
        < SPECIES_MEDIUM_CONFIDENCE
    ):

        return {
            "success": True,
            "scientific_name": pi_name,
            "common_name": plantid_result.get(
                "common_name",
                ""
            ),
            "confidence": pi_confidence,
            "confidence_label": confidence_label(
                pi_confidence
            ),
            "status": (
                "Identified by Plant.id"
            ),
            "message": (
                "Plant.id produced a strong "
                "species match, while Pl@ntNet "
                "returned a low-confidence result."
            ),
            "verification": (
                "Single-engine strong match"
            ),
            "source": "Plant.id",
            "alternatives": [
                {
                    "scientific_name": pn_name,
                    "common_name": plantnet_result.get(
                        "common_name",
                        ""
                    ),
                    "confidence": pn_confidence
                }
            ]
        }

    # --------------------------------------------------------
    # UNCERTAIN DISAGREEMENT
    # --------------------------------------------------------

    if pn_confidence >= pi_confidence:

        selected = plantnet_result
        other = plantid_result

    else:

        selected = plantid_result
        other = plantnet_result

    return {
        "success": True,
        "scientific_name": selected.get(
            "scientific_name",
            "Unknown Plant"
        ),
        "common_name": selected.get(
            "common_name",
            ""
        ),
        "confidence": selected.get(
            "confidence",
            0
        ),
        "confidence_label": "Low Confidence",
        "status": (
            "AI results are uncertain"
        ),
        "message": (
            "The two AI engines returned "
            "different species. The result "
            "should not be treated as confirmed."
        ),
        "verification": (
            "AI engines disagree"
        ),
        "source": (
            selected.get(
                "source",
                "AI"
            )
        ),
        "alternatives": [
            {
                "scientific_name": other.get(
                    "scientific_name",
                    "Unknown"
                ),
                "common_name": other.get(
                    "common_name",
                    ""
                ),
                "confidence": other.get(
                    "confidence",
                    0
                )
            }
        ]
        + selected.get(
            "alternatives",
            []
        )
    }


# ============================================================
# PERENUAL PLANT PROFILE
# ============================================================

def empty_plant_profile(message=""):
    """
    Default plant profile.
    """

    return {
        "available": False,
        "source": "Plant care database",
        "message": message,

        "temperature": "Not available",
        "minimum_temperature": "Not available",
        "maximum_temperature": "Not available",

        "humidity": "Not available",
        "water": "Not available",
        "soil_moisture": "Not available",
        "soil_type": "Not available",
        "ph": "Not available",
        "sunlight": "Not available",
        "wind_tolerance": "Not available",
        "rainfall": "Not available",
        "growing_season": "Not available",
        "growth_stages": "Not available",
        "irrigation": "Not available",
        "kc": "Not available"
    }


def clean_profile_value(value):
    """
    Convert Perenual values to readable text.
    """

    if value is None:
        return "Not available"

    if isinstance(value, list):

        if not value:
            return "Not available"

        return ", ".join(
            str(item)
            for item in value
        )

    if isinstance(value, dict):

        if "value" in value:
            return str(value["value"])

        return json.dumps(
            value,
            ensure_ascii=False
        )

    value = str(value).strip()

    if not value:
        return "Not available"

    return value


def search_perenual_species(scientific_name):
    """
    Search Perenual regular species API.

    This is intentionally used before the details endpoint.
    """

    if not PERENUAL_API_KEY:
        return None

    try:

        params = {
            "key": PERENUAL_API_KEY,
            "q": scientific_name,
            "page": 1
        }

        response = requests.get(
            PERENUAL_SPECIES_LIST_URL,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return None

        data = response.json()

        plants = data.get(
            "data",
            []
        )

        if not plants:
            return None

        # Prefer exact scientific-name match
        normalized_target = (
            normalize_scientific_name(
                scientific_name
            ).lower()
        )

        best = plants[0]

        for plant in plants:

            candidate = normalize_scientific_name(
                plant.get(
                    "scientific_name",
                    ""
                )
            ).lower()

            if candidate == normalized_target:

                best = plant
                break

        return best

    except Exception as error:

        print(
            f"Perenual species search unavailable: "
            f"{error}"
        )

        return None


def get_perenual_details(plant_id):
    """
    Get detailed Perenual plant information.

    If the free plan returns 429/upgrade restriction,
    the function safely returns None.
    """

    if not PERENUAL_API_KEY:
        return None

    if not plant_id:
        return None

    try:

        params = {
            "key": PERENUAL_API_KEY
        }

        response = requests.get(
            f"{PERENUAL_DETAILS_URL}/{plant_id}",
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            # Especially handle free-plan restriction
            if response.status_code == 429:
                print(
                    "Perenual details API is "
                    "currently restricted by the plan."
                )

            return None

        return response.json()

    except Exception as error:

        print(
            f"Perenual details unavailable: "
            f"{error}"
        )

        return None


def build_plant_profile(
    scientific_name,
    common_name=""
):
    """
    Build plant requirement profile.

    Perenual is optional.
    It never blocks plant identification.
    """

    profile = empty_plant_profile()

    if not scientific_name:
        profile["message"] = (
            "Plant identification is required "
            "before plant requirements can be loaded."
        )
        return profile

    # --------------------------------------------------------
    # STEP 1: Search regular species endpoint
    # --------------------------------------------------------

    species_data = search_perenual_species(
        scientific_name
    )

    if species_data:

        profile["source"] = (
            "Perenual plant database"
        )

        profile["available"] = True

        profile["watering"] = clean_profile_value(
            species_data.get("watering")
        )

        profile["sunlight"] = clean_profile_value(
            species_data.get("sunlight")
        )

        profile["cycle"] = clean_profile_value(
            species_data.get("cycle")
        )

        profile["hardiness"] = clean_profile_value(
            species_data.get("hardiness")
        )

        profile["care_level"] = clean_profile_value(
            species_data.get("care_level")
        )

        profile["description"] = clean_profile_value(
            species_data.get("description")
        )

        # Keep the requested agriculture fields
        profile["water"] = profile["watering"]

        profile["growing_season"] = profile["cycle"]

        profile["minimum_temperature"] = (
            "Not available"
        )

        profile["maximum_temperature"] = (
            "Not available"
        )

        profile["temperature"] = (
            "Not available"
        )

        profile["humidity"] = (
            "Not available"
        )

        profile["soil_moisture"] = (
            "Not available"
        )

        profile["soil_type"] = (
            "Not available"
        )

        profile["ph"] = (
            "Not available"
        )

        profile["wind_tolerance"] = (
            "Not available"
        )

        profile["rainfall"] = (
            "Not available"
        )

        profile["growth_stages"] = (
            "Not available"
        )

        profile["irrigation"] = (
            profile["watering"]
        )

        profile["kc"] = (
            "Not available"
        )

        # ----------------------------------------------------
        # STEP 2: Try details API
        # ----------------------------------------------------

        plant_id = species_data.get(
            "id"
        )

        details = get_perenual_details(
            plant_id
        )

        if details:

            profile["available"] = True
            profile["source"] = (
                "Perenual plant database"
            )

            # Watering
            profile["water"] = clean_profile_value(
                details.get(
                    "watering"
                )
                or details.get(
                    "watering_general_benchmark"
                )
                or species_data.get(
                    "watering"
                )
            )

            profile["irrigation"] = (
                profile["water"]
            )

            # Sunlight
            profile["sunlight"] = clean_profile_value(
                details.get(
                    "sunlight"
                )
                or species_data.get(
                    "sunlight"
                )
            )

            # Soil
            profile["soil_type"] = clean_profile_value(
                details.get(
                    "soil"
                )
                or details.get(
                    "soil_type"
                )
                or details.get(
                    "soil_texture"
                )
            )

            # pH
            profile["ph"] = clean_profile_value(
                details.get(
                    "soil_ph"
                )
                or details.get(
                    "ph"
                )
                or details.get(
                    "soil_ph_range"
                )
            )

            # Temperature
            profile["temperature"] = clean_profile_value(
                details.get(
                    "temperature"
                )
                or details.get(
                    "temperature_range"
                )
                or details.get(
                    "hardiness"
                )
            )

            profile["minimum_temperature"] = (
                clean_profile_value(
                    details.get(
                        "minimum_temperature"
                    )
                    or details.get(
                        "min_temperature"
                    )
                )
            )

            profile["maximum_temperature"] = (
                clean_profile_value(
                    details.get(
                        "maximum_temperature"
                    )
                    or details.get(
                        "max_temperature"
                    )
                )
            )

            # Humidity
            profile["humidity"] = clean_profile_value(
                details.get(
                    "humidity"
                )
                or details.get(
                    "humidity_requirement"
                )
            )

            # Rainfall
            profile["rainfall"] = clean_profile_value(
                details.get(
                    "rainfall"
                )
                or details.get(
                    "rainfall_requirement"
                )
            )

            # Growth / cycle
            profile["growing_season"] = clean_profile_value(
                details.get(
                    "cycle"
                )
                or details.get(
                    "growth_cycle"
                )
                or species_data.get(
                    "cycle"
                )
            )

            profile["growth_stages"] = clean_profile_value(
                details.get(
                    "growth_stages"
                )
                or details.get(
                    "growth_stage"
                )
            )

            # Wind
            profile["wind_tolerance"] = clean_profile_value(
                details.get(
                    "wind_tolerance"
                )
                or details.get(
                    "wind"
                )
            )

            # Kc
            profile["kc"] = clean_profile_value(
                details.get(
                    "kc"
                )
                or details.get(
                    "crop_coefficient"
                )
                or details.get(
                    "crop_coefficient_kc"
                )
            )

            # Soil moisture
            profile["soil_moisture"] = clean_profile_value(
                details.get(
                    "soil_moisture"
                )
                or details.get(
                    "soil_moisture_range"
                )
            )

            profile["description"] = clean_profile_value(
                details.get(
                    "description"
                )
                or details.get(
                    "description_short"
                )
                or species_data.get(
                    "description"
                )
            )

        else:

            profile["message"] = (
                "Basic plant information was found. "
                "Some advanced growing requirements "
                "are not available from the current "
                "free API access."
            )

    else:

        profile["available"] = False

        profile["message"] = (
            "Plant identification is available, "
            "but detailed plant growing requirements "
            "are not available from the current "
            "plant-care API access."
        )

    return profile


# ============================================================
# PLANTNET DISEASE DETECTION
# ============================================================

def detect_with_plantnet_disease(image_path):
    """
    Analyze disease separately from plant identification.
    """

    if not PLANTNET_API_KEY:

        return {
            "success": False,
            "source": "Pl@ntNet Disease",
            "error": (
                "Pl@ntNet API key is not configured."
            )
        }

    try:

        with open(
            image_path,
            "rb"
        ) as image_file:

            files = {
                "images": (
                    os.path.basename(image_path),
                    image_file,
                    "image/jpeg"
                )
            }

            data = {
                "organs": "auto"
            }

            params = {
                "api-key": PLANTNET_API_KEY,
                "lang": "en",
                "nb-results": 5
            }

            response = requests.post(
                PLANTNET_DISEASE_API_URL,
                params=params,
                files=files,
                data=data,
                timeout=60
            )

        if response.status_code != 200:

            return {
                "success": False,
                "source": "Pl@ntNet Disease",
                "error": (
                    f"Disease API error "
                    f"({response.status_code})"
                )
            }

        result = response.json()

        results = result.get(
            "results",
            []
        )

        if not results:

            return {
                "success": False,
                "source": "Pl@ntNet Disease",
                "error": (
                    "No disease result returned."
                )
            }

        best = results[0]

        disease_name = (
            best.get("name")
            or best.get("disease", {}).get(
                "name"
            )
            or "Unknown condition"
        )

        confidence = safe_percentage(
            best.get(
                "score",
                best.get(
                    "confidence",
                    0
                )
            )
        )

        description = best.get(
            "description",
            ""
        )

        alternatives = []

        for item in results[1:5]:

            item_name = (
                item.get("name")
                or item.get(
                    "disease",
                    {}
                ).get(
                    "name"
                )
                or "Unknown condition"
            )

            item_confidence = safe_percentage(
                item.get(
                    "score",
                    item.get(
                        "confidence",
                        0
                    )
                )
            )

            alternatives.append({
                "name": item_name,
                "confidence": item_confidence
            })

        return {
            "success": True,
            "source": "Pl@ntNet Disease AI",
            "disease": disease_name,
            "confidence": confidence,
            "confidence_label": confidence_label(
                confidence
            ),
            "description": description,
            "alternatives": alternatives,
            "raw": result
        }

    except Exception as error:

        return {
            "success": False,
            "source": "Pl@ntNet Disease",
            "error": str(error)
        }


# ============================================================
# DISEASE ANALYSIS
# ============================================================

def add_disease_analysis(
    image_path,
    plant_confidence
):
    """
    Run disease detection only after plant
    identification reaches the minimum threshold.
    """

    # --------------------------------------------------------
    # Do not run disease confirmation for uncertain plant
    # --------------------------------------------------------

    if plant_confidence < SPECIES_MEDIUM_CONFIDENCE:

        return {
            "available": False,
            "confirmed": False,
            "status": (
                "Disease analysis not confirmed"
            ),
            "message": (
                "Plant identification confidence "
                "is too low for reliable disease "
                "analysis."
            ),
            "disease": "",
            "confidence": 0.0,
            "confidence_label": "Low Confidence",
            "source": "",
            "alternatives": []
        }

    disease_result = (
        detect_with_plantnet_disease(
            image_path
        )
    )

    if not disease_result.get(
        "success",
        False
    ):

        return {
            "available": False,
            "confirmed": False,
            "status": (
                "Disease analysis unavailable"
            ),
            "message": (
                "The disease analysis service "
                "could not return a valid result."
            ),
            "disease": "",
            "confidence": 0.0,
            "confidence_label": "Low Confidence",
            "source": "",
            "alternatives": []
        }

    confidence = disease_result.get(
        "confidence",
        0
    )

    # --------------------------------------------------------
    # LOW CONFIDENCE
    # --------------------------------------------------------

    if confidence < DISEASE_ACCEPTANCE_THRESHOLD:

        return {
            "available": True,
            "confirmed": False,
            "status": (
                "Disease analysis is not confirmed"
            ),
            "message": (
                "The disease model returned "
                "low confidence. No disease is "
                "being confirmed. Plant identification "
                "and disease detection are separate "
                "AI tasks."
            ),
            "disease": disease_result.get(
                "disease",
                ""
            ),
            "confidence": confidence,
            "confidence_label": "Low Confidence",
            "source": disease_result.get(
                "source",
                ""
            ),
            "alternatives": disease_result.get(
                "alternatives",
                []
            )
        }

    # --------------------------------------------------------
    # CONFIRMED DISEASE
    # --------------------------------------------------------

    return {
        "available": True,
        "confirmed": True,
        "status": (
            "Possible disease detected"
        ),
        "message": (
            "The disease model returned "
            "a confidence level above the "
            "current acceptance threshold."
        ),
        "disease": disease_result.get(
            "disease",
            ""
        ),
        "confidence": confidence,
        "confidence_label": confidence_label(
            confidence
        ),
        "source": disease_result.get(
            "source",
            ""
        ),
        "description": disease_result.get(
            "description",
            ""
        ),
        "alternatives": disease_result.get(
            "alternatives",
            []
        )
    }


# ============================================================
# OPEN-METEO WEATHER / ENVIRONMENT API
# ============================================================

def get_open_meteo_data(
    latitude,
    longitude,
    forecast_days=7
):
    """
    Fetch live environment data from Open-Meteo.

    Data includes:
    - Temperature
    - Humidity
    - Wind speed
    - Rain
    - Precipitation
    - Solar radiation
    - Soil temperature
    - Soil moisture
    - ET0
    - VPD
    - Forecast
    """

    try:

        latitude = float(latitude)
        longitude = float(longitude)

    except Exception:

        return {
            "success": False,
            "error": (
                "Latitude and longitude "
                "must be valid numbers."
            )
        }

    # Keep forecast between 1 and 16 days
    try:
        forecast_days = int(
            forecast_days
        )
    except Exception:
        forecast_days = 7

    forecast_days = max(
        1,
        min(
            forecast_days,
            16
        )
    )

    current_variables = ",".join([
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "precipitation",
        "rain",
        "showers",
        "soil_temperature_0cm",
        "soil_moisture_0_to_1cm",
        "et0_fao_evapotranspiration",
        "vapour_pressure_deficit",
        "shortwave_radiation",
        "sunshine_duration"
    ])

    hourly_variables = ",".join([
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "showers",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "soil_temperature_0_to_7cm",
        "soil_moisture_0_to_7cm",
        "et0_fao_evapotranspiration",
        "vapour_pressure_deficit",
        "shortwave_radiation",
        "sunshine_duration"
    ])

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": current_variables,

        "hourly": hourly_variables,

        "forecast_days": forecast_days,

        "timezone": "auto"
    }

    try:

        response = requests.get(
            OPEN_METEO_API_URL,
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            return {
                "success": False,
                "error": (
                    f"Open-Meteo API error "
                    f"({response.status_code})"
                )
            }

        data = response.json()

        current = data.get(
            "current",
            {}
        )

        current_units = data.get(
            "current_units",
            {}
        )

        hourly = data.get(
            "hourly",
            {}
        )

        hourly_units = data.get(
            "hourly_units",
            {}
        )

        environment = {
            "latitude": data.get(
                "latitude"
            ),
            "longitude": data.get(
                "longitude"
            ),
            "timezone": data.get(
                "timezone"
            ),
            "elevation": data.get(
                "elevation"
            ),

            "current": {
                "time": current.get(
                    "time"
                ),

                "temperature": current.get(
                    "temperature_2m"
                ),

                "humidity": current.get(
                    "relative_humidity_2m"
                ),

                "wind_speed": current.get(
                    "wind_speed_10m"
                ),

                "wind_direction": current.get(
                    "wind_direction_10m"
                ),

                "wind_gust": current.get(
                    "wind_gusts_10m"
                ),

                "precipitation": current.get(
                    "precipitation"
                ),

                "rain": current.get(
                    "rain"
                ),

                "showers": current.get(
                    "showers"
                ),

                "soil_temperature": current.get(
                    "soil_temperature_0cm"
                ),

                "soil_moisture": current.get(
                    "soil_moisture_0_to_1cm"
                ),

                "et0": current.get(
                    "et0_fao_evapotranspiration"
                ),

                "vpd": current.get(
                    "vapour_pressure_deficit"
                ),

                "solar_radiation": current.get(
                    "shortwave_radiation"
                ),

                "sunshine_duration": current.get(
                    "sunshine_duration"
                )
            },

            "current_units": current_units,

            "hourly": hourly,

            "hourly_units": hourly_units,

            "forecast_days": forecast_days,

            "source": "Open-Meteo"
        }

        return {
            "success": True,
            "data": environment
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "error": (
                "Open-Meteo request timed out."
            )
        }

    except requests.exceptions.RequestException as error:

        return {
            "success": False,
            "error": (
                f"Open-Meteo connection error: "
                f"{error}"
            )
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error)
        }


# ============================================================
# OPENWEATHER CITY SEARCH API
# ============================================================


def get_openweather_data(city):
    """Fetch current weather and forecast rain probability from OpenWeather."""

    city = (city or "").strip()

    if not city:
        return {
            "success": False,
            "error": "Please enter a city name."
        }

    if not OPENWEATHER_API_KEY:
        return {
            "success": False,
            "error": "OpenWeather API key is missing. Check your .env file."
        }

    current_url = "https://api.openweathermap.org/data/2.5/weather"
    forecast_url = "https://api.openweathermap.org/data/2.5/forecast"

    try:
        current_response = requests.get(
            current_url,
            params={
                "q": city,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric"
            },
            timeout=15
        )

        if current_response.status_code == 404:
            return {
                "success": False,
                "error": "City not found. Please check the city name."
            }

        if current_response.status_code == 401:
            return {
                "success": False,
                "error": "OpenWeather API key is invalid or not active yet."
            }

        current_response.raise_for_status()
        data = current_response.json()

        current = data.get("main", {})
        weather_list = data.get("weather", [])
        wind = data.get("wind", {})
        weather_info = weather_list[0] if weather_list else {}

        # Forecast data: probability of precipitation for the next 3-hour periods
        rain_chance = None
        forecast_rainfall = None
        forecast_period = None
        forecast_note = "Forecast unavailable"

        forecast_response = requests.get(
            forecast_url,
            params={
                "lat": data["coord"]["lat"],
                "lon": data["coord"]["lon"],
                "appid": OPENWEATHER_API_KEY,
                "units": "metric"
            },
            timeout=15
        )

        if forecast_response.ok:
            forecast_data = forecast_response.json()
            forecast_items = forecast_data.get("list", [])

            if forecast_items:
                next_period = forecast_items[0]
                probability = next_period.get("pop")

                if probability is not None:
                    rain_chance = round(float(probability) * 100)

                rain_details = next_period.get("rain", {})
                forecast_rainfall = rain_details.get("3h", 0)

                forecast_period = next_period.get("dt_txt")
                forecast_note = "Next 3-hour forecast period"

        return {
            "success": True,
            "data": {
                "city": data.get("name", city),
                "country": data.get("sys", {}).get("country", ""),
                "temperature": current.get("temp"),
                "feels_like": current.get("feels_like"),
                "humidity": current.get("humidity"),
                "pressure": current.get("pressure"),
                "condition": weather_info.get(
                    "description", "Unknown"
                ).title(),
                "icon": weather_info.get("icon", ""),
                "wind_speed": wind.get("speed"),
                "clouds": data.get("clouds", {}).get("all"),
                "visibility": data.get("visibility"),
                "rain_chance": rain_chance,
                "forecast_rainfall": forecast_rainfall,
                "forecast_period": forecast_period,
                "forecast_note": forecast_note,
                "source": "OpenWeather"
            }
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Weather request timed out. Please try again."
        }

    except requests.exceptions.RequestException:
        return {
            "success": False,
            "error": "Could not connect to OpenWeather. Check your internet or API service."
        }

    except (ValueError, TypeError, KeyError):
        return {
            "success": False,
            "error": "Could not read the weather data."
        }

   
# ============================================================
# SAVE WEATHER DATA
# ============================================================

def save_weather_record(weather_data):
    """
    Save latest weather/environment result.
    """

    try:

        weather_file = "weather.json"

        old_data = load_json(
            weather_file,
            []
        )

        if not isinstance(
            old_data,
            list
        ):
            old_data = []

        record = {
            "timestamp": now_string(),
            "data": weather_data
        }

        old_data.append(record)

        # Keep latest 100 records
        old_data = old_data[-100:]

        save_json(
            weather_file,
            old_data
        )

    except Exception as error:

        print(
            f"Weather save error: {error}"
        )


# ============================================================
# WEATHER API ROUTE
# ============================================================

@app.route(
    "/api/weather",
    methods=["GET"]
)
def weather_api():

    latitude = request.args.get(
        "latitude"
    )

    longitude = request.args.get(
        "longitude"
    )

    forecast_days = request.args.get(
        "forecast_days",
        7
    )

    if latitude is None or longitude is None:

        return jsonify({
            "success": False,
            "error": (
                "latitude and longitude "
                "are required."
            )
        }), 400

    result = get_open_meteo_data(
        latitude,
        longitude,
        forecast_days
    )

    if not result.get(
        "success",
        False
    ):

        return jsonify(
            result
        ), 500

    save_weather_record(
        result["data"]
    )

    return jsonify(
        result
    )


# ============================================================
# PLANT SUITABILITY API
# ============================================================

@app.route("/api/plant-suitability", methods=["GET"])
def plant_suitability_api():
    plant_name = request.args.get(
        "plant_name", ""
    ).strip()

    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")

    if not plant_name:
        return jsonify({
            "success": False,
            "error": "plant_name is required."
        }), 400

    if latitude is None or longitude is None:
        return jsonify({
            "success": False,
            "error": "latitude and longitude are required."
        }), 400

    try:
        latitude = float(latitude)
        longitude = float(longitude)

        if not -90 <= latitude <= 90:
            raise ValueError("Invalid latitude.")

        if not -180 <= longitude <= 180:
            raise ValueError("Invalid longitude.")

    except ValueError:
        return jsonify({
            "success": False,
            "error": "Please provide valid coordinates."
        }), 400

    try:
        profile = get_plant_requirements(plant_name)

        weather_result = get_open_meteo_data(
            latitude,
            longitude,
            7
        )

        if not weather_result.get("success"):
            return jsonify({
                "success": False,
                "error": weather_result.get(
                    "error",
                    "Weather data unavailable."
                )
            }), 502

        weather = weather_result.get("data", {})

        save_weather_record(weather)

        current = weather.get("current", {})

        return jsonify({
            "success": True,
            "plant": {
                "scientific_name": profile.get(
                    "scientific_name",
                    "Not Available"
                ),
                "common_name": profile.get(
                    "common_name",
                    "Not Available"
                ),
                "family": profile.get(
                    "family",
                    "Not Available"
                ),
                "cycle": profile.get(
                    "cycle",
                    "Not Available"
                ),
                "soil_type": profile.get(
                    "soil_type",
                    "Not Available"
                ),
                "sunlight": profile.get(
                    "sunlight",
                    "Not Available"
                ),
                "temperature_min": profile.get(
                    "temperature_min",
                    "Not Available"
                ),
                "temperature_max": profile.get(
                    "temperature_max",
                    "Not Available"
                ),
                "data_status": profile.get(
                    "data_status",
                    "Incomplete"
                ),
                "source": profile.get(
                    "source",
                    "Not Available"
                )
            },
            "environment": current,
            "forecast": weather.get("daily", {}),
            "suitability": {
                "status": "Insufficient data",
                "message": (
                    "A complete suitability verdict requires "
                    "verified plant limits and relevant soil "
                    "measurements."
                )
            },
            "weather_source": "Open-Meteo"
        })

    except Exception as error:
        app.logger.exception(
            "Plant suitability API failed"
        )

        return jsonify({
            "success": False,
            "error": "Could not generate plant suitability report."
        }), 500
        
# ============================================================
# AGROVISION BROWSER AUTHENTICATION
# ============================================================

def get_users():
    """Load registered users from users.json."""

    users = load_json("users.json", [])

    if not isinstance(users, list):
        return []

    return [
        user for user in users
        if isinstance(user, dict)
    ]


def current_user():
    """Return the logged-in user's session data."""

    user_id = session.get("user_id")

    if user_id is None:
        return None

    for user in get_users():
        if str(user.get("id")) == str(user_id):
            return user

    return None


def login_required(view_function):
    """Protect browser pages from unauthenticated access."""

    from functools import wraps

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        user = current_user()

        if not user:
            session.clear()
            flash("Please log in to continue.")
            return redirect(url_for("login_page"))

        return view_function(*args, **kwargs)

    return wrapped_view


@app.route("/login", methods=["GET", "POST"])
def login_page():
    """Authenticate an existing AgroVision user."""

    if request.method == "GET":
        if current_user():
            return redirect(url_for("role_home"))

        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Enter both username and password.")
        return redirect(url_for("login_page"))

    user = next(
        (
            item for item in get_users()
            if item.get("username") == username
            and item.get("password") == password
        ),
        None
    )

    if not user:
        flash("Invalid username or password.")
        return redirect(url_for("login_page"))

    session.clear()
    session["user_id"] = user.get("id")
    session["username"] = user.get("username")
    session["name"] = user.get("name", user.get("username"))
    session["role"] = str(user.get("role", "farmer")).lower()

    return redirect(url_for("role_home"))


@app.route("/role-home")
@login_required
def role_home():
    """Redirect users to the page allowed for their role."""

    role = session.get("role")

    if role == "admin":
        return redirect(url_for("dashboard_page"))

    if role == "farmer":
        return redirect(url_for("farmer_dashboard"))

    session.clear()
    flash("Your account has an invalid role.")
    return redirect(url_for("login_page"))


@app.route("/farmer-dashboard")
@login_required
def farmer_dashboard():
    """Display the farmer's browser dashboard."""

    if session.get("role") != "farmer":
        flash("This page is available to farmer accounts only.")
        return redirect(url_for("role_home"))

    return render_template(
        "farmer_dashboard.html",
        name=session.get("name", "Farmer"),
        username=session.get("username", "")
    )


@app.route("/logout")
def logout_page():
    """End the browser session."""

    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login_page"))



# ============================================================
# WEB DASHBOARD
# ============================================================

from collections import Counter


def dashboard_records(filename):
    """Return a list of records from a JSON file."""

    data = load_json(filename, [])

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return [
                    item for item in value
                    if isinstance(item, dict)
                ]
        return [data]

    return []


def dashboard_value(record, key, default="Unknown"):
    """Return a clean display value."""

    value = record.get(key, default)

    if value is None or not str(value).strip():
        return default

    # Repair common UTF-8 text decoded with the wrong encoding.
    value = str(value).replace("Â°C", "°C")

    return value



@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard_page():
    """Display the admin dashboard with agriculture statistics."""

    # Only admin can access this dashboard
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    # Load database records
    farmers = dashboard_records("farmers.json")
    farms = dashboard_records("farms.json")
    crops = dashboard_records("crops.json")
    soil = dashboard_records("soil.json")
    irrigation = dashboard_records("irrigation.json")
    weather = dashboard_records("weather.json")
    diseases = dashboard_records("disease.json")
    fertilizer = dashboard_records("fertilizer.json")

    # Crop status and season statistics
    crop_status = Counter(
        dashboard_value(item, "status")
        for item in crops
    )

    crop_seasons = Counter(
        dashboard_value(item, "season")
        for item in crops
    )

    # Farm district statistics
    districts = Counter(
        dashboard_value(item, "district")
        for item in farms
    )

    # Dashboard summary cards
    stats = {
        "farmers": len(farmers),
        "farms": len(farms),
        "crops": len(crops),
        "soil": len(soil),
        "irrigation": len(irrigation),
        "weather": len(weather),
        "diseases": len(diseases),
        "fertilizer": len(fertilizer),
    }

    # Latest soil record
    latest_soil = None

    if soil:
        item = soil[-1]

        latest_soil = {
            "soil_type": dashboard_value(
                item, "soil_type"
            ),
            "ph": dashboard_value(item, "ph"),
            "nitrogen": dashboard_value(
                item, "nitrogen"
            ),
            "phosphorus": dashboard_value(
                item, "phosphorus"
            ),
            "potassium": dashboard_value(
                item, "potassium"
            ),
            "moisture": dashboard_value(
                item, "moisture"
            ),
        }

    # Latest weather record
    latest_weather = None

    if weather:
        item = weather[-1]

        latest_weather = {
            "city": dashboard_value(item, "city"),
            "temperature": dashboard_value(
                item, "temperature"
            ),
            "humidity": dashboard_value(
                item, "humidity"
            ),
            "rain": dashboard_value(item, "rain"),
            "wind": dashboard_value(item, "wind"),
            "condition": dashboard_value(
                item, "condition"
            ),
        }

    # Latest 8 disease records
    recent_diseases = []

    for item in reversed(diseases[-8:]):
        timestamp = dashboard_value(
            item, "timestamp"
        )

        date = (
            timestamp[:10]
            if timestamp != "Unknown"
            else "Unknown"
        )

        confidence = item.get(
            "confidence",
            item.get("disease_confidence", "Unknown")
        )

        if confidence is not None:
            try:
                confidence = round(
                    float(confidence), 2
                )
            except (TypeError, ValueError):
                confidence = "Unknown"

        recent_diseases.append({
            "disease": dashboard_value(
                item, "disease"
            ),
            "confidence": confidence,
            "date": date,
        })

    # Render admin dashboard
    return render_template(
        "dashboard.html",
        stats=stats,
        crop_status=crop_status,
        crop_seasons=crop_seasons,
        districts=districts,
        latest_soil=latest_soil,
        latest_weather=latest_weather,
        recent_diseases=recent_diseases,
    )
    
    
# ============================================================
# AGROVISION ADMIN MODULE ROUTES
# ============================================================

ADMIN_MODULES = {
    "farmers": {
        "title": "Farmer Management",
        "file": "farmers.json",
    },
    "farms": {
        "title": "Farm Management",
        "file": "farms.json",
    },
    "crops": {
        "title": "Crop Management",
        "file": "crops.json",
    },
    "soil": {
        "title": "Soil Management",
        "file": "soil.json",
    },
    "weather": {
        "title": "Weather Management",
        "file": "weather.json",
    },
    "fertilizer": {
        "title": "Fertilizer Recommendation",
        "file": "fertilizer.json",
    },
    "diseases": {
        "title": "Disease Detection & Records",
        "file": "disease.json",
    },
    "irrigation": {
        "title": "Irrigation Management",
        "file": "irrigation.json",
    },
    "market": {
        "title": "Market Price",
        "file": "market.json",
    },
    "reports": {
        "title": "Reports",
        "file": "reports.json",
    },
}


@app.route("/admin/module/<module_name>")
@login_required
def admin_module_page(module_name):
    """Display records for a selected admin module."""

    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    module = ADMIN_MODULES.get(module_name)

    if module is None:
        flash("Module not found.")
        return redirect(url_for("dashboard_page"))

    records = dashboard_records(module["file"])

    return render_template(
        "module_page.html",
        module_name=module_name,
        module_title=module["title"],
        records=records,
        database_file=module["file"],
    )
    
# ============================================================
# AGROVISION REPORTS CENTER
# ============================================================

@app.route("/admin/reports-center", methods=["GET", "POST"])
@login_required
def reports_center():
    """Add, view, edit and update agriculture reports."""

    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    reports_file = "reports.json"

    categories = [
        "Farmer & Farm Reports",
        "Crop & Soil Reports",
        "Weather & Irrigation Reports",
        "Fertilizer Recommendation Reports",
        "Disease Detection Reports",
        "Market Price Reports",
    ]

    reports = dashboard_records(reports_file)

    if not isinstance(reports, list):
        reports = []

    edit_id = request.args.get("edit", "").strip()
    edit_report = None

    if edit_id:
        edit_report = next(
            (
                report for report in reports
                if str(report.get("report_id", "")) == edit_id
            ),
            None,
        )

        if edit_report is None:
            flash("Report not found.")

    if request.method == "POST":
        action = request.form.get("action", "add").strip()
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        notes = request.form.get("notes", "").strip()

        if action not in ("add", "update"):
            flash("Invalid report action.")
            return redirect(url_for("reports_center"))

        if not title or not description or category not in categories:
            flash("Please enter a title, valid category and description.")
            return redirect(url_for("reports_center"))

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if action == "add":
            report_numbers = []

            for report in reports:
                report_id = str(report.get("report_id", ""))
                if report_id.startswith("R") and report_id[1:].isdigit():
                    report_numbers.append(int(report_id[1:]))

            next_number = max(report_numbers, default=0) + 1
            report_id = f"R{next_number:03d}"

            new_report = {
                "report_id": report_id,
                "title": title,
                "category": category,
                "description": description,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            }

            reports.append(new_report)

            if save_json(reports_file, reports):
                flash(f"Report {report_id} added successfully.")
            else:
                flash("Could not save the report.")

            return redirect(url_for("reports_center"))

        report_id = request.form.get("report_id", "").strip()

        existing_report = next(
            (
                report for report in reports
                if str(report.get("report_id", "")) == report_id
            ),
            None,
        )

        if existing_report is None:
            flash("Report not found. Update cancelled.")
            return redirect(url_for("reports_center"))

        existing_report.update({
            "title": title,
            "category": category,
            "description": description,
            "notes": notes,
            "updated_at": now,
        })

        if save_json(reports_file, reports):
            flash(f"Report {report_id} updated successfully.")
        else:
            flash("Could not update the report.")

        return redirect(url_for("reports_center"))

    selected_category = request.args.get("category", "").strip()

    if selected_category in categories:
        visible_reports = [
            report for report in reports
            if report.get("category") == selected_category
        ]
    else:
        selected_category = ""
        visible_reports = reports

    return render_template(
        "reports_center.html",
        reports=visible_reports,
        categories=categories,
        edit_report=edit_report,
        selected_category=selected_category,
    )

# ============================================================
# AGROVISION MARKET PRICE SEARCH
# ============================================================

import csv
from pathlib import Path
from difflib import get_close_matches
from datetime import datetime


MARKET_CSV_FILE = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "mandi_prices.csv"
)


def load_mandi_prices():
    """Load mandi prices from the CSV dataset."""
    if not MARKET_CSV_FILE.exists():
        return []

    try:
        with open(
            MARKET_CSV_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:
            return list(csv.DictReader(file))

    except (OSError, UnicodeError, csv.Error):
        return []


def market_clean(value):
    """Normalize text for case-insensitive searching."""
    return " ".join(str(value or "").strip().casefold().split())


@app.route("/admin/market-price", methods=["GET", "POST"])
@login_required
def market_price_search():
    """Search mandi prices using the CSV dataset."""

    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    crop = request.values.get("crop", "").strip()
    state = request.values.get("state", "").strip()
    district = request.values.get("district", "").strip()

    all_rows = load_mandi_prices()

    crop_names = sorted({
        str(row.get("Commodity", "")).strip()
        for row in all_rows
        if str(row.get("Commodity", "")).strip()
    })

    state_names = sorted({
        str(row.get("State", "")).strip()
        for row in all_rows
        if str(row.get("State", "")).strip()
        
    })
    
    state_district_map = {}

    for row in all_rows:
        state_name = str(row.get("State", "")).strip()
        district_name = str(row.get("District", "")).strip()

        if state_name and district_name:
            state_district_map.setdefault(state_name, set()).add(
                district_name
            )

    state_district_map = {
        state: sorted(districts)
        for state, districts in state_district_map.items()
    }

    results = []
    suggestions = []
    crop_matches = []

    if crop:
        crop_key = market_clean(crop)

        # Search exact crop name first.
        exact_matches = [
            row for row in all_rows
            if market_clean(row.get("Commodity")) == crop_key
        ]

        if exact_matches:
            crop_matches = exact_matches
        else:
            # Try partial matching.
            crop_matches = [
                row for row in all_rows
                if crop_key in market_clean(row.get("Commodity"))
                or market_clean(row.get("Commodity")) in crop_key
            ]

            # Suggest similar crop names.
            if not crop_matches:
                suggestions = get_close_matches(
                    crop,
                    crop_names,
                    n=10,
                    cutoff=0.35
                )

        # Apply state and district filters.
        for row in crop_matches:
            if state and market_clean(row.get("State")) != market_clean(state):
                continue

            if district and market_clean(district) not in market_clean(
                row.get("District")
            ):
                continue

            results.append(row)

        # Sort by arrival date, newest first.
        def date_key(row):
            value = str(row.get("Arrival_Date", "")).strip()

            for date_format in ("%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value, date_format)
                except ValueError:
                    pass

            return datetime.min

        results.sort(key=date_key, reverse=True)

    # Calculate price summary.
    def parse_market_price(value):
        try:
            cleaned = str(value or "").replace(",", "").strip()
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    min_prices = [
        parse_market_price(row.get("Min_x0020_Price"))
        for row in results
    ]
    max_prices = [
        parse_market_price(row.get("Max_x0020_Price"))
        for row in results
    ]
    modal_prices = [
        parse_market_price(row.get("Modal_x0020_Price"))
        for row in results
    ]

    min_prices = [p for p in min_prices if p is not None]
    max_prices = [p for p in max_prices if p is not None]
    modal_prices = [p for p in modal_prices if p is not None]

    price_summary = {
        "minimum": min(min_prices) if min_prices else None,
        "maximum": max(max_prices) if max_prices else None,
        "average_modal": (
            sum(modal_prices) / len(modal_prices)
            if modal_prices else None
        ),
    }

    return render_template(
        "market_price.html",
        module_title="Market Price",
        crop=crop,
        state=state,
        district=district,
        crop_names=crop_names,
        state_names=state_names,
        results=results[:200],
        total_results=len(results),
        suggestions=suggestions,
        csv_found=MARKET_CSV_FILE.exists(),
        state_district_map=state_district_map,
        price_summary=price_summary,
    )



@app.route("/admin/irrigation")
@login_required
def irrigation_management_web():
    """Display weather-based irrigation advice and saved records."""

    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    city = request.args.get("city", "").strip()
    live_weather = None
    weather_error = None
    advice = None

    irrigation_records = dashboard_records("irrigation.json")
    soil_records = dashboard_records("soil.json")

    if city:
        result = get_openweather_data(city)

        if result.get("success"):
            live_weather = result.get("data", {})

            rain_chance = live_weather.get("rain_chance")
            rainfall = live_weather.get("forecast_rainfall")
            temperature = live_weather.get("temperature")

            if (
                rain_chance is not None and rain_chance >= 60
            ) or (
                rainfall is not None and rainfall > 0
            ):
                advice = (
                    "Rain is possible in the next forecast period. "
                    "Check soil moisture before irrigating; postpone "
                    "irrigation if the root zone is already sufficiently wet."
                )
            elif temperature is not None and temperature >= 35:
                advice = (
                    "High temperature detected. Check crop condition "
                    "and soil moisture; irrigate only if the crop needs it."
                )
            else:
                advice = (
                    "No strong rain signal in the next forecast period. "
                    "Check soil moisture and crop needs before deciding "
                    "whether to irrigate."
                )
        else:
            weather_error = result.get(
                "error", "Unable to fetch live weather."
            )

    return render_template(
        "irrigation.html",
        irrigation_records=irrigation_records,
        soil_records=soil_records,
        city=city,
        live_weather=live_weather,
        weather_error=weather_error,
        advice=advice
    )


# ============================================================
# IRRIGATION MANAGEMENT - ADD, EDIT, DELETE
# ============================================================

@app.route("/admin/irrigation/add", methods=["GET", "POST"])
@login_required
def add_irrigation_web():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    if request.method == "POST":
        records = dashboard_records("irrigation.json")

        crop_name = request.form.get("crop_name", "").strip()
        farm_id = request.form.get("farm_id", "").strip()
        irrigation_date = request.form.get("irrigation_date", "").strip()
        water_liters = request.form.get("water_liters", "").strip()
        duration_minutes = request.form.get("duration_minutes", "").strip()
        status = request.form.get("status", "Scheduled").strip()
        notes = request.form.get("notes", "").strip()

        if not crop_name or not farm_id or not irrigation_date:
            flash("Crop name, Farm ID and irrigation date are required.")
            return render_template("irrigation_form.html", record=None)

        try:
            water_liters = float(water_liters)
            duration_minutes = int(duration_minutes)
            if water_liters < 0 or duration_minutes < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Water and duration must be valid non-negative numbers.")
            return render_template("irrigation_form.html", record=None)

        existing_ids = [
            str(item.get("irrigation_id", ""))
            for item in records
        ]
        number = 1
        while f"IR{number:03d}" in existing_ids:
            number += 1

        records.append({
            "irrigation_id": f"IR{number:03d}",
            "farm_id": farm_id,
            "crop_name": crop_name,
            "irrigation_date": irrigation_date,
            "water_liters": water_liters,
            "duration_minutes": duration_minutes,
            "status": status,
            "notes": notes
        })

        save_json("irrigation.json", records)
        flash("Irrigation record added successfully!")
        return redirect(url_for("irrigation_management_web"))

    return render_template("irrigation_form.html", record=None)


@app.route(
    "/admin/irrigation/edit/<int:record_index>",
    methods=["GET", "POST"]
)
@login_required
def edit_irrigation_web(record_index):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    records = dashboard_records("irrigation.json")

    if record_index < 0 or record_index >= len(records):
        flash("Irrigation record not found.")
        return redirect(url_for("irrigation_management_web"))

    if request.method == "POST":
        crop_name = request.form.get("crop_name", "").strip()
        farm_id = request.form.get("farm_id", "").strip()
        irrigation_date = request.form.get("irrigation_date", "").strip()
        water_liters = request.form.get("water_liters", "").strip()
        duration_minutes = request.form.get("duration_minutes", "").strip()
        status = request.form.get("status", "Scheduled").strip()
        notes = request.form.get("notes", "").strip()

        if not crop_name or not farm_id or not irrigation_date:
            flash("Crop name, Farm ID and irrigation date are required.")
            return render_template(
                "irrigation_form.html",
                record=records[record_index],
                record_index=record_index
            )

        try:
            water_liters = float(water_liters)
            duration_minutes = int(duration_minutes)
            if water_liters < 0 or duration_minutes < 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Water and duration must be valid non-negative numbers.")
            return render_template(
                "irrigation_form.html",
                record=records[record_index],
                record_index=record_index
            )

        old_record = records[record_index]
        records[record_index] = {
            **old_record,
            "farm_id": farm_id,
            "crop_name": crop_name,
            "irrigation_date": irrigation_date,
            "water_liters": water_liters,
            "duration_minutes": duration_minutes,
            "status": status,
            "notes": notes
        }

        save_json("irrigation.json", records)
        flash("Irrigation record updated successfully!")
        return redirect(url_for("irrigation_management_web"))

    return render_template(
        "irrigation_form.html",
        record=records[record_index],
        record_index=record_index
    )


@app.route(
    "/admin/irrigation/delete/<int:record_index>",
    methods=["POST"]
)
@login_required
def delete_irrigation_web(record_index):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    records = dashboard_records("irrigation.json")

    if record_index < 0 or record_index >= len(records):
        flash("Irrigation record not found.")
    else:
        records.pop(record_index)
        save_json("irrigation.json", records)
        flash("Irrigation record deleted successfully!")

    return redirect(url_for("irrigation_management_web"))



# ============================================================
# FERTILIZER MANAGEMENT - ADD, EDIT, DELETE
# ============================================================

@app.route("/admin/fertilizer/add", methods=["GET", "POST"])
@login_required
def add_fertilizer_web():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    if request.method == "POST":
        records = dashboard_records("fertilizer.json")

        crop = request.form.get("crop", "").strip()
        name = request.form.get("name", "").strip()
        nutrient = request.form.get("nutrient", "").strip()
        quantity = request.form.get("quantity", "").strip()
        schedule = request.form.get("schedule", "").strip()
        fertilizer_type = request.form.get("type", "").strip()

        if not all([crop, name, nutrient, quantity, schedule, fertilizer_type]):
            flash("Please fill in all fertilizer fields.")
            return render_template("fertilizer_form.html", record=None)

        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Quantity must be greater than zero.")
            return render_template("fertilizer_form.html", record=None)

        existing_ids = [
            str(item.get("fertilizer_id", ""))
            for item in records
        ]

        number = 1
        while f"F{number:03d}" in existing_ids:
            number += 1

        records.append({
            "fertilizer_id": f"F{number:03d}",
            "crop": crop,
            "name": name,
            "nutrient": nutrient,
            "quantity": quantity,
            "schedule": schedule,
            "type": fertilizer_type
        })

        if save_json("fertilizer.json", records):
            flash("Fertilizer record added successfully!")
        else:
            flash("Could not save fertilizer record.")

        return redirect(url_for("admin_module_page", module_name="fertilizer"))

    return render_template("fertilizer_form.html", record=None)


@app.route("/admin/fertilizer/edit/<int:record_index>", methods=["GET", "POST"])
@login_required
def edit_fertilizer_web(record_index):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    records = dashboard_records("fertilizer.json")

    if record_index < 0 or record_index >= len(records):
        flash("Fertilizer record not found.")
        return redirect(url_for("admin_module_page", module_name="fertilizer"))

    record = records[record_index]

    if request.method == "POST":
        crop = request.form.get("crop", "").strip()
        name = request.form.get("name", "").strip()
        nutrient = request.form.get("nutrient", "").strip()
        quantity = request.form.get("quantity", "").strip()
        schedule = request.form.get("schedule", "").strip()
        fertilizer_type = request.form.get("type", "").strip()

        if not all([crop, name, nutrient, quantity, schedule, fertilizer_type]):
            flash("Please fill in all fertilizer fields.")
            return render_template("fertilizer_form.html", record=record)

        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            flash("Quantity must be greater than zero.")
            return render_template("fertilizer_form.html", record=record)

        records[record_index] = {
            **record,
            "crop": crop,
            "name": name,
            "nutrient": nutrient,
            "quantity": quantity,
            "schedule": schedule,
            "type": fertilizer_type
        }

        if save_json("fertilizer.json", records):
            flash("Fertilizer record updated successfully!")
        else:
            flash("Could not update fertilizer record.")

        return redirect(url_for("admin_module_page", module_name="fertilizer"))

    return render_template("fertilizer_form.html", record=record)


@app.route("/admin/fertilizer/delete/<int:record_index>", methods=["POST"])
@login_required
def delete_fertilizer_web(record_index):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    records = dashboard_records("fertilizer.json")

    if record_index < 0 or record_index >= len(records):
        flash("Fertilizer record not found.")
    else:
        records.pop(record_index)

        if save_json("fertilizer.json", records):
            flash("Fertilizer record deleted successfully!")
        else:
            flash("Could not delete fertilizer record.")

    return redirect(url_for("admin_module_page", module_name="fertilizer"))


# ============================================================
# FARMER MANAGEMENT - WEB ROUTES
# ============================================================

from flask import request, render_template, redirect, url_for, flash, session


@app.route("/admin/farmers")
@login_required
def farmer_management():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farmers = dashboard_records("farmers.json")

    return render_template(
        "farmers.html",
        farmers=farmers
    )


@app.route("/admin/farmers/add", methods=["GET", "POST"])
@login_required
def add_farmer():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    if request.method == "POST":
        farmers = dashboard_records("farmers.json")

        farmer_id = request.form.get("farmer_id", "").strip()
        name = request.form.get("name", "").strip()

        if not name:
            flash("Farmer name is required.")
            return redirect(url_for("add_farmer"))

        if not farmer_id:
            existing_numbers = []
            for farmer in farmers:
                fid = str(farmer.get("farmer_id", ""))
                if fid.startswith("F") and fid[1:].isdigit():
                    existing_numbers.append(int(fid[1:]))

            farmer_id = f"F{max(existing_numbers, default=0) + 1:03d}"

        if any(
            str(f.get("farmer_id", "")).lower() == farmer_id.lower()
            for f in farmers
        ):
            flash("This Farmer ID already exists.")
            return redirect(url_for("add_farmer"))

        farmer = {
            "farmer_id": farmer_id,
            "name": name,
            "age": request.form.get("age", "").strip(),
            "gender": request.form.get("gender", "").strip(),
            "mobile": request.form.get("mobile", "").strip(),
            "state": request.form.get("state", "").strip(),
            "district": request.form.get("district", "").strip(),
            "village": request.form.get("village", "").strip(),
            "land": request.form.get("land", "").strip()
        }

        farmers.append(farmer)
        save_json("farmers.json", farmers)

        flash("Farmer added successfully!")
        return redirect(url_for("farmer_management"))

    return render_template("farmer_form.html", farmer=None)


@app.route("/admin/farmers/edit/<farmer_id>", methods=["GET", "POST"])
@login_required
def edit_farmer(farmer_id):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farmers = dashboard_records("farmers.json")
    farmer = next(
        (f for f in farmers if str(f.get("farmer_id")) == farmer_id),
        None
    )

    if farmer is None:
        flash("Farmer not found.")
        return redirect(url_for("farmer_management"))

    if request.method == "POST":
        farmer["name"] = request.form.get("name", "").strip()
        farmer["age"] = request.form.get("age", "").strip()
        farmer["gender"] = request.form.get("gender", "").strip()
        farmer["mobile"] = request.form.get("mobile", "").strip()
        farmer["state"] = request.form.get("state", "").strip()
        farmer["district"] = request.form.get("district", "").strip()
        farmer["village"] = request.form.get("village", "").strip()
        farmer["land"] = request.form.get("land", "").strip()
        
        save_json("farmers.json", farmers)
        flash("Farmer updated successfully!")
        return redirect(url_for("farmer_management"))

    return render_template("farmer_form.html", farmer=farmer)


@app.route("/admin/farmers/delete/<farmer_id>", methods=["POST"])
@login_required
def delete_farmer(farmer_id):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farmers = dashboard_records("farmers.json")
    updated_farmers = [
        f for f in farmers
        if str(f.get("farmer_id")) != farmer_id
    ]

    if len(updated_farmers) == len(farmers):
        flash("Farmer not found.")
    else:
        save_json("farmers.json", updated_farmers)
        flash("Farmer deleted successfully!")

    return redirect(url_for("farmer_management"))


# ============================================================
# FARM MANAGEMENT - WEB ROUTES
# ============================================================

@app.route("/admin/farms")
@login_required
def farm_management():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farms = dashboard_records("farms.json")
    farmers = dashboard_records("farmers.json")

    return render_template(
        "farms.html",
        farms=farms,
        farmers=farmers
    )


@app.route("/admin/farms/add", methods=["GET", "POST"])
@login_required
def add_farm():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farmers = dashboard_records("farmers.json")

    if request.method == "POST":
        farms = dashboard_records("farms.json")

        farmer_id = request.form.get("farmer_id", "").strip()
        farm_name = request.form.get("farm_name", "").strip()

        if not farmer_id or not any(
            str(f.get("farmer_id", "")) == farmer_id for f in farmers
        ):
            flash("Please select a valid farmer.")
            return redirect(url_for("add_farm"))

        if not farm_name:
            flash("Farm name is required.")
            return redirect(url_for("add_farm"))

        existing_numbers = []
        for farm in farms:
            fid = str(farm.get("farm_id", ""))
            if fid.startswith("FM") and fid[2:].isdigit():
                existing_numbers.append(int(fid[2:]))

        farm_id = f"FM{max(existing_numbers, default=0) + 1:03d}"

        farms.append({
            "farm_id": farm_id,
            "farmer_id": farmer_id,
            "farm_name": farm_name,
            "land_area": request.form.get("land_area", "").strip(),
            "soil_type": request.form.get("soil_type", "").strip(),
            "irrigation_type": request.form.get("irrigation_type", "").strip(),
            "village": request.form.get("village", "").strip(),
            "district": request.form.get("district", "").strip()
        })

        save_json("farms.json", farms)
        flash("Farm added successfully!")
        return redirect(url_for("farm_management"))

    return render_template("farm_form.html", farm=None, farmers=farmers)


@app.route("/admin/farms/edit/<farm_id>", methods=["GET", "POST"])
@login_required
def edit_farm(farm_id):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farms = dashboard_records("farms.json")
    farmers = dashboard_records("farmers.json")

    farm = next(
        (f for f in farms if str(f.get("farm_id", "")) == farm_id),
        None
    )

    if farm is None:
        flash("Farm not found.")
        return redirect(url_for("farm_management"))

    if request.method == "POST":
        farmer_id = request.form.get("farmer_id", "").strip()

        if not any(
            str(f.get("farmer_id", "")) == farmer_id for f in farmers
        ):
            flash("Please select a valid farmer.")
            return redirect(url_for("edit_farm", farm_id=farm_id))

        farm.update({
            "farmer_id": farmer_id,
            "farm_name": request.form.get("farm_name", "").strip(),
            "land_area": request.form.get("land_area", "").strip(),
            "soil_type": request.form.get("soil_type", "").strip(),
            "irrigation_type": request.form.get("irrigation_type", "").strip(),
            "village": request.form.get("village", "").strip(),
            "district": request.form.get("district", "").strip()
        })

        if not farm["farm_name"]:
            flash("Farm name is required.")
            return redirect(url_for("edit_farm", farm_id=farm_id))

        save_json("farms.json", farms)
        flash("Farm updated successfully!")
        return redirect(url_for("farm_management"))

    return render_template("farm_form.html", farm=farm, farmers=farmers)


@app.route("/admin/farms/delete/<farm_id>", methods=["POST"])
@login_required
def delete_farm(farm_id):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farms = dashboard_records("farms.json")
    updated_farms = [
        f for f in farms
        if str(f.get("farm_id", "")) != farm_id
    ]

    if len(updated_farms) == len(farms):
        flash("Farm not found.")
    else:
        save_json("farms.json", updated_farms)
        flash("Farm deleted successfully!")

    return redirect(url_for("farm_management"))


# ============================================================
# CROP MANAGEMENT - WEB ROUTES
# ============================================================

@app.route("/admin/crops")
@login_required
def crop_management():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    crops = dashboard_records("crops.json")
    farms = dashboard_records("farms.json")
    farmers = dashboard_records("farmers.json")

    return render_template(
        "crops.html",
        crops=crops,
        farms=farms,
        farmers=farmers
    )


@app.route("/admin/crops/add", methods=["GET", "POST"])
@login_required
def add_crop():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farms = dashboard_records("farms.json")
    farmers = dashboard_records("farmers.json")

    if request.method == "POST":
        crops = dashboard_records("crops.json")

        farm_id = request.form.get("farm_id", "").strip()
        crop_name = request.form.get("crop_name", "").strip()

        farm = next(
            (f for f in farms if str(f.get("farm_id", "")) == farm_id),
            None
        )

        if farm is None:
            flash("Please select a valid farm.")
            return redirect(url_for("add_crop"))

        if not crop_name:
            flash("Crop name is required.")
            return redirect(url_for("add_crop"))

        existing_numbers = []
        for crop in crops:
            cid = str(crop.get("crop_id", ""))
            if cid.startswith("C") and cid[1:].isdigit():
                existing_numbers.append(int(cid[1:]))

        crop_id = f"C{max(existing_numbers, default=0) + 1:03d}"

        crops.append({
            "crop_id": crop_id,
            "farm_id": farm_id,
            "farmer_id": farm.get("farmer_id", ""),
            "crop_name": crop_name,
            "crop_variety": request.form.get("crop_variety", "").strip(),
            "season": request.form.get("season", "").strip(),
            "sowing_date": request.form.get("sowing_date", "").strip(),
            "expected_harvest_date": request.form.get(
                "expected_harvest_date", ""
            ).strip(),
            "status": request.form.get("status", "Planned").strip()
        })

        save_json("crops.json", crops)
        flash("Crop added successfully!")
        return redirect(url_for("crop_management"))

    return render_template(
        "crop_form.html",
        crop=None,
        farms=farms,
        farmers=farmers
    )


@app.route("/admin/crops/edit/<crop_id>", methods=["GET", "POST"])
@login_required
def edit_crop(crop_id):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    crops = dashboard_records("crops.json")
    farms = dashboard_records("farms.json")
    farmers = dashboard_records("farmers.json")

    crop = next(
        (c for c in crops if str(c.get("crop_id", "")) == crop_id),
        None
    )

    if crop is None:
        flash("Crop not found.")
        return redirect(url_for("crop_management"))

    if request.method == "POST":
        farm_id = request.form.get("farm_id", "").strip()
        farm = next(
            (f for f in farms if str(f.get("farm_id", "")) == farm_id),
            None
        )

        crop_name = request.form.get("crop_name", "").strip()

        if farm is None or not crop_name:
            flash("Select a valid farm and enter a crop name.")
            return redirect(url_for("edit_crop", crop_id=crop_id))

        crop.update({
            "farm_id": farm_id,
            "farmer_id": farm.get("farmer_id", ""),
            "crop_name": crop_name,
            "crop_variety": request.form.get("crop_variety", "").strip(),
            "season": request.form.get("season", "").strip(),
            "sowing_date": request.form.get("sowing_date", "").strip(),
            "expected_harvest_date": request.form.get(
                "expected_harvest_date", ""
            ).strip(),
            "status": request.form.get("status", "Planned").strip()
        })

        save_json("crops.json", crops)
        flash("Crop updated successfully!")
        return redirect(url_for("crop_management"))

    return render_template(
        "crop_form.html",
        crop=crop,
        farms=farms,
        farmers=farmers
    )


@app.route("/admin/crops/delete/<crop_id>", methods=["POST"])
@login_required
def delete_crop(crop_id):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    crops = dashboard_records("crops.json")
    updated_crops = [
        c for c in crops
        if str(c.get("crop_id", "")) != crop_id
    ]

    if len(updated_crops) == len(crops):
        flash("Crop not found.")
    else:
        save_json("crops.json", updated_crops)
        flash("Crop deleted successfully!")

    return redirect(url_for("crop_management"))


# ============================================================
# SOIL MANAGEMENT - WEB ROUTES
# ============================================================

@app.route("/admin/soil")
@login_required
def soil_management():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    soils = dashboard_records("soil.json")
    farms = dashboard_records("farms.json")

    return render_template(
        "soil.html",
        soils=soils,
        farms=farms
    )


@app.route("/admin/soil/add", methods=["GET", "POST"])
@login_required
def add_soil():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    farms = dashboard_records("farms.json")

    if request.method == "POST":
        soils = dashboard_records("soil.json")
        farm_id = request.form.get("farm_id", "").strip()

        farm = next(
            (f for f in farms
             if str(f.get("farm_id", "")) == farm_id),
            None
        )

        if farm is None:
            flash("Please select a valid farm.")
            return redirect(url_for("add_soil"))

        numbers = []
        for item in soils:
            sid = str(item.get("soil_id", ""))
            if sid.startswith("S") and sid[1:].isdigit():
                numbers.append(int(sid[1:]))

        soil_id = f"S{max(numbers, default=0) + 1:03d}"

        soils.append({
            "soil_id": soil_id,
            "farm_id": farm_id,
            "soil_type": request.form.get("soil_type", "").strip(),
            "ph": request.form.get("ph", "").strip(),
            "nitrogen": request.form.get("nitrogen", "").strip(),
            "phosphorus": request.form.get("phosphorus", "").strip(),
            "potassium": request.form.get("potassium", "").strip(),
            "moisture": request.form.get("moisture", "").strip(),
            "temperature": request.form.get("temperature", "").strip(),
            "organic_carbon": request.form.get("organic_carbon", "").strip(),
            "report_date": request.form.get("report_date", "").strip(),
            "notes": request.form.get("notes", "").strip()
        })

        save_json("soil.json", soils)
        flash("Soil record added successfully!")
        return redirect(url_for("soil_management"))

    return render_template("soil_form.html", soil=None, farms=farms)


@app.route("/admin/soil/edit/<soil_id>", methods=["GET", "POST"])
@login_required
def edit_soil(soil_id):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    soils = dashboard_records("soil.json")
    farms = dashboard_records("farms.json")

    soil = next(
        (s for s in soils
         if str(s.get("soil_id", "")) == soil_id),
        None
    )

    if soil is None:
        flash("Soil record not found.")
        return redirect(url_for("soil_management"))

    if request.method == "POST":
        farm_id = request.form.get("farm_id", "").strip()

        farm = next(
            (f for f in farms
             if str(f.get("farm_id", "")) == farm_id),
            None
        )

        if farm is None:
            flash("Please select a valid farm.")
            return redirect(url_for("edit_soil", soil_id=soil_id))

        soil.update({
            "farm_id": farm_id,
            "soil_type": request.form.get("soil_type", "").strip(),
            "ph": request.form.get("ph", "").strip(),
            "nitrogen": request.form.get("nitrogen", "").strip(),
            "phosphorus": request.form.get("phosphorus", "").strip(),
            "potassium": request.form.get("potassium", "").strip(),
            "moisture": request.form.get("moisture", "").strip(),
            "temperature": request.form.get("temperature", "").strip(),
            "organic_carbon": request.form.get("organic_carbon", "").strip(),
            "report_date": request.form.get("report_date", "").strip(),
            "notes": request.form.get("notes", "").strip()
        })

        save_json("soil.json", soils)
        flash("Soil record updated successfully!")
        return redirect(url_for("soil_management"))

    return render_template("soil_form.html", soil=soil, farms=farms)


@app.route("/admin/soil/delete/<soil_id>", methods=["POST"])
@login_required
def delete_soil(soil_id):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    soils = dashboard_records("soil.json")

    updated_soils = [
        item for item in soils
        if str(item.get("soil_id", "")) != soil_id
    ]

    if len(updated_soils) == len(soils):
        flash("Soil record not found.")
    else:
        save_json("soil.json", updated_soils)
        flash("Soil record deleted successfully!")

    return redirect(url_for("soil_management"))


# ============================================================
# WEATHER MANAGEMENT - WEB ROUTES
# ============================================================


@app.route("/admin/weather")
@login_required
def weather_management_web():

    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    # Existing saved weather reports
    weather_records = dashboard_records("weather.json")

    # City entered by the admin
    search_city = request.args.get("city", "").strip()

    # Live weather result and error
    live_weather = None
    weather_error = None

    if search_city:
        # Fetch current weather from OpenWeather API
        result = get_openweather_data(search_city)

        if result.get("success"):
            live_weather = result.get("data", {})
        else:
            weather_error = result.get(
                "error",
                "Unable to fetch live weather."
            )

        # Also filter existing saved records
        weather_records = [
            item for item in weather_records
            if search_city.lower() in
            str(item.get("city", "")).lower()
        ]

    return render_template(
        "weather.html",
        weather_records=weather_records,
        search_city=search_city,
        live_weather=live_weather,
        weather_error=weather_error
    )


@app.route("/admin/weather/add", methods=["GET", "POST"])
@login_required
def add_weather_web():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    if request.method == "POST":
        weather_records = dashboard_records("weather.json")

        city = request.form.get("city", "").strip()
        temperature = request.form.get("temperature", "").strip()
        humidity = request.form.get("humidity", "").strip()
        rain = request.form.get("rain", "").strip()
        wind = request.form.get("wind", "").strip()
        condition = request.form.get("condition", "").strip()
        report_date = request.form.get("report_date", "").strip()

        if not city or not condition:
            flash("City and weather condition are required.")
            return render_template("weather_form.html", weather=None)

        try:
            temp_value = float(temperature)
            humidity_value = float(humidity)
            rain_value = float(rain)
            wind_value = float(wind)

            if not 0 <= humidity_value <= 100:
                raise ValueError("Humidity must be between 0 and 100.")

            if not 0 <= rain_value <= 100:
                raise ValueError("Rain chance must be between 0 and 100.")

            if wind_value < 0:
                raise ValueError("Wind speed cannot be negative.")

        except ValueError as error:
            flash(str(error) if str(error) else "Enter valid weather values.")
            return render_template("weather_form.html", weather=None)

        weather_records.append({
            "city": city,
            "temperature": f"{temp_value:g}°C",
            "humidity": f"{humidity_value:g}%",
            "rain": f"{rain_value:g}%",
            "wind": f"{wind_value:g} km/h",
            "condition": condition,
            "report_date": report_date
        })

        save_json("weather.json", weather_records)
        flash("Weather report added successfully!")
        return redirect(url_for("weather_management_web"))

    return render_template("weather_form.html", weather=None)


@app.route("/admin/weather/edit/<int:record_index>", methods=["GET", "POST"])
@login_required
def edit_weather_web(record_index):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    weather_records = dashboard_records("weather.json")

    if record_index < 0 or record_index >= len(weather_records):
        flash("Weather record not found.")
        return redirect(url_for("weather_management_web"))

    weather = weather_records[record_index]

    if request.method == "POST":
        city = request.form.get("city", "").strip()
        temperature = request.form.get("temperature", "").strip()
        humidity = request.form.get("humidity", "").strip()
        rain = request.form.get("rain", "").strip()
        wind = request.form.get("wind", "").strip()
        condition = request.form.get("condition", "").strip()
        report_date = request.form.get("report_date", "").strip()

        if not city or not condition:
            flash("City and weather condition are required.")
            return render_template(
                "weather_form.html",
                weather=weather,
                record_index=record_index
            )

        try:
            temp_value = float(temperature)
            humidity_value = float(humidity)
            rain_value = float(rain)
            wind_value = float(wind)

            if not 0 <= humidity_value <= 100:
                raise ValueError("Humidity must be between 0 and 100.")

            if not 0 <= rain_value <= 100:
                raise ValueError("Rain chance must be between 0 and 100.")

            if wind_value < 0:
                raise ValueError("Wind speed cannot be negative.")

        except ValueError as error:
            flash(str(error) if str(error) else "Enter valid weather values.")
            return render_template(
                "weather_form.html",
                weather=weather,
                record_index=record_index
            )

        weather.update({
            "city": city,
            "temperature": f"{temp_value:g}°C",
            "humidity": f"{humidity_value:g}%",
            "rain": f"{rain_value:g}%",
            "wind": f"{wind_value:g} km/h",
            "condition": condition,
            "report_date": report_date
        })

        save_json("weather.json", weather_records)
        flash("Weather report updated successfully!")
        return redirect(url_for("weather_management_web"))

    return render_template(
        "weather_form.html",
        weather=weather,
        record_index=record_index
    )


@app.route("/admin/weather/delete/<int:record_index>", methods=["POST"])
@login_required
def delete_weather_web(record_index):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    weather_records = dashboard_records("weather.json")

    if record_index < 0 or record_index >= len(weather_records):
        flash("Weather record not found.")
    else:
        weather_records.pop(record_index)
        save_json("weather.json", weather_records)
        flash("Weather report deleted successfully!")

    return redirect(url_for("weather_management_web"))


# ============================================================
# MAIN PLANT IDENTIFICATION ROUTE
# ============================================================

@app.route(
    "/",
    methods=["GET", "POST"]
)
def index():

    if request.method == "GET":

        return render_template(
            "disease.html"
        )

    # --------------------------------------------------------
    # CHECK IMAGE
    # --------------------------------------------------------

    if "image" not in request.files:

        return render_template(
            "disease.html",
            error=(
                "Please select or capture "
                "a plant image."
            )
        )

    image = request.files["image"]

    if not image or not image.filename:

        return render_template(
            "disease.html",
            error=(
                "No image was selected."
            )
        )

    if not allowed_file(
        image.filename
    ):

        return render_template(
            "disease.html",
            error=(
                "Only JPG, JPEG, PNG or WEBP "
                "images are allowed."
            )
        )

    # --------------------------------------------------------
    # SAVE IMAGE
    # --------------------------------------------------------

    original_filename = secure_filename(
        image.filename
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    filename = (
        timestamp
        + "_"
        + original_filename
    )

    image_path = (
        UPLOAD_FOLDER
        / filename
    )

    try:

        image.save(
            str(image_path)
        )

    except Exception as error:

        return render_template(
            "disease.html",
            error=(
                f"Image save failed: {error}"
            )
        )

    # --------------------------------------------------------
    # STEP 1
    # PL@NTNET SPECIES
    # --------------------------------------------------------

    print()
    print("=" * 65)
    print("AGROVISION - PL@NTNET SPECIES ANALYSIS")
    print("=" * 65)

    plantnet_species = (
        detect_with_plantnet_species(
            str(image_path)
        )
    )

    if plantnet_species.get(
        "success"
    ):

        print(
            "Pl@ntNet:",
            plantnet_species.get(
                "scientific_name"
            ),
            plantnet_species.get(
                "confidence"
            ),
            "%"
        )

    else:

        print(
            "Pl@ntNet species error:",
            plantnet_species.get(
                "error"
            )
        )

    # --------------------------------------------------------
    # STEP 2
    # PLANT.ID SPECIES
    # --------------------------------------------------------

    print()
    print("=" * 65)
    print("AGROVISION - PLANT.ID SPECIES ANALYSIS")
    print("=" * 65)

    plantid_species = (
        detect_with_plant_id(
            str(image_path)
        )
    )

    if plantid_species.get(
        "success"
    ):

        print(
            "Plant.id:",
            plantid_species.get(
                "scientific_name"
            ),
            plantid_species.get(
                "confidence"
            ),
            "%"
        )

    else:

        print(
            "Plant.id error:",
            plantid_species.get(
                "error"
            )
        )

    # --------------------------------------------------------
    # STEP 3
    # COMPARE BOTH AI ENGINES
    # --------------------------------------------------------

    final_identification = (
        compare_species_results(
            plantnet_species,
            plantid_species
        )
    )

    scientific_name = (
        final_identification.get(
            "scientific_name",
            "Unknown Plant"
        )
    )

    common_name = (
        final_identification.get(
            "common_name",
            ""
        )
    )

    plant_confidence = (
        final_identification.get(
            "confidence",
            0
        )
    )

    # --------------------------------------------------------
    # STEP 4
    # PLANT PROFILE
    # --------------------------------------------------------

    print()
    print("=" * 65)
    print("AGROVISION - PLANT REQUIREMENTS")
    print("=" * 65)

    plant_profile = build_plant_profile(
        scientific_name,
        common_name
    )

    # --------------------------------------------------------
    # STEP 5
    # DISEASE ANALYSIS
    # --------------------------------------------------------

    print()
    print("=" * 65)
    print("AGROVISION - DISEASE ANALYSIS")
    print("=" * 65)

    disease_analysis = (
        add_disease_analysis(
            str(image_path),
            plant_confidence
        )
    )

    print(
        "Disease:",
        disease_analysis.get(
            "disease",
            "Not confirmed"
        )
    )

    print(
        "Disease confidence:",
        disease_analysis.get(
            "confidence",
            0
        ),
        "%"
    )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    result = {
        "image_url": (
            "/uploads/"
            + filename
        ),

        "scientific_name": scientific_name,

        "common_name": common_name,

        "source": final_identification.get(
            "source",
            ""
        ),

        "status": final_identification.get(
            "status",
            ""
        ),

        "confidence": plant_confidence,

        "confidence_label": final_identification.get(
            "confidence_label",
            confidence_label(
                plant_confidence
            )
        ),

        "message": final_identification.get(
            "message",
            ""
        ),

        "verification": final_identification.get(
            "verification",
            ""
        ),

        "alternatives": final_identification.get(
            "alternatives",
            []
        ),

        "plant_profile": plant_profile,

        "disease_analysis": disease_analysis,

        "analyzed_at": now_string()
    }

    # --------------------------------------------------------
    # SAVE ANALYSIS TO disease.json
    # --------------------------------------------------------

    try:

        disease_records = load_json(
            "disease.json",
            []
        )

        if not isinstance(
            disease_records,
            list
        ):
            disease_records = []

        disease_records.append({
            "timestamp": now_string(),
            "image": filename,
            "scientific_name": scientific_name,
            "common_name": common_name,
            "plant_confidence": plant_confidence,
            "plant_status": final_identification.get(
                "status",
                ""
            ),
            "disease": disease_analysis.get(
                "disease",
                ""
            ),
            "disease_confidence": disease_analysis.get(
                "confidence",
                0
            ),
            "disease_confirmed": disease_analysis.get(
                "confirmed",
                False
            )
        })

        # Keep last 500 analysis records
        disease_records = disease_records[-500:]

        save_json(
            "disease.json",
            disease_records
        )

    except Exception as error:

        print(
            f"Disease database save error: {error}"
        )

    # --------------------------------------------------------
    # CONSOLE RESULT
    # --------------------------------------------------------

    print()
    print("=" * 65)
    print("AGROVISION - FINAL RESULT")
    print("=" * 65)

    print(
        "Scientific Name :",
        scientific_name
    )

    print(
        "Common Name     :",
        common_name
    )

    print(
        "Confidence      :",
        plant_confidence,
        "%"
    )

    print(
        "Status          :",
        final_identification.get(
            "status"
        )
    )

    print(
        "Verification    :",
        final_identification.get(
            "verification"
        )
    )

    print(
        "Disease         :",
        disease_analysis.get(
            "disease",
            "Not confirmed"
        )
    )

    print(
        "Disease Conf.   :",
        disease_analysis.get(
            "confidence",
            0
        ),
        "%"
    )

    print("=" * 65)
    print()

    return render_template(
        "disease.html",
        result=result
    )


# ============================================================
# UPLOADED IMAGE ROUTE
# ============================================================

@app.route(
    "/uploads/<filename>"
)
def uploaded_file(filename):

    return send_from_directory(
        str(UPLOAD_FOLDER),
        filename
    )


# ============================================================
# API STATUS
# ============================================================

@app.route(
    "/api/status",
    methods=["GET"]
)
def api_status():

    return jsonify({
        "success": True,
        "application": "AGROVISION",
        "status": "running",

        "apis": {
            "plantnet_species": bool(
                PLANTNET_API_KEY
            ),

            "plantnet_disease": bool(
                PLANTNET_API_KEY
            ),

            "plant_id": bool(
                PLANT_ID_API_KEY
            ),

            "perenual": bool(
                PERENUAL_API_KEY
            ),

            "open_meteo": True
        },

        "timestamp": now_string()
    })


# ============================================================
# 413 FILE TOO LARGE
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    return render_template(
        "disease.html",
        error=(
            "Image is too large. "
            "Maximum allowed size is 50 MB."
        )
    ), 413


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@app.errorhandler(500)
def internal_server_error(error):

    print(
        f"Internal server error: {error}"
    )

    return render_template(
        "disease.html",
        error=(
            "An internal server error occurred. "
            "Please try again."
        )
    ), 500

# ================= DISEASE RECORD CRUD =================

@app.route("/admin/diseases/add", methods=["GET", "POST"])
@login_required
def disease_record_add():
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    if request.method == "POST":
        records = load_json("disease.json", [])

        record = {
            "timestamp": now_string(),
            "common_name": request.form.get("common_name", "").strip(),
            "scientific_name": request.form.get("scientific_name", "").strip(),
            "plant_confidence": request.form.get("plant_confidence", "").strip(),
            "disease": request.form.get("disease", "").strip() or "Not confirmed",
            "disease_confidence": request.form.get("disease_confidence", "").strip(),
            "disease_confirmed": request.form.get("disease_confirmed") == "yes",
            "image": request.form.get("image", "").strip() or "N/A",
        }

        records.append(record)
        save_json("disease.json", records)

        flash("Disease record added successfully.")
        return redirect(url_for("admin_module_page", module_name="diseases"))

    return render_template(
        "disease_record_form.html",
        record=None,
        page_title="Add Disease Record"
    )


@app.route("/admin/diseases/edit/<int:record_index>", methods=["GET", "POST"])
@login_required
def disease_record_edit(record_index):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    records = load_json("disease.json", [])

    if record_index < 0 or record_index >= len(records):
        flash("Disease record not found.")
        return redirect(url_for("admin_module_page", module_name="diseases"))

    if request.method == "POST":
        record = records[record_index]

        record["common_name"] = request.form.get("common_name", "").strip()
        record["scientific_name"] = request.form.get("scientific_name", "").strip()
        record["plant_confidence"] = request.form.get("plant_confidence", "").strip()
        record["disease"] = request.form.get("disease", "").strip() or "Not confirmed"
        record["disease_confidence"] = request.form.get("disease_confidence", "").strip()
        record["disease_confirmed"] = request.form.get("disease_confirmed") == "yes"
        record["image"] = request.form.get("image", "").strip() or "N/A"

        records[record_index] = record
        save_json("disease.json", records)

        flash("Disease record updated successfully.")
        return redirect(url_for("admin_module_page", module_name="diseases"))

    return render_template(
        "disease_record_form.html",
        record=records[record_index],
        page_title="Edit Disease Record"
    )


@app.route("/admin/diseases/delete/<int:record_index>", methods=["POST"])
@login_required
def disease_record_delete(record_index):
    if session.get("role") != "admin":
        flash("Admin access is required.")
        return redirect(url_for("role_home"))

    records = load_json("disease.json", [])

    if record_index < 0 or record_index >= len(records):
        flash("Disease record not found.")
    else:
        records.pop(record_index)
        save_json("disease.json", records)
        flash("Disease record deleted successfully.")

    return redirect(url_for("admin_module_page", module_name="diseases"))


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("🌱 AGROVISION - AI PLANT & DISEASE SYSTEM")
    print("------------------------------------------")
    print("Server starting...")
    print("Open: http://127.0.0.1:5000")
    print()

    print(
        "Pl@ntNet API Key:",
        "Loaded"
        if PLANTNET_API_KEY
        else "Not Loaded"
    )

    print(
        "Plant.id API Key:",
        "Loaded"
        if PLANT_ID_API_KEY
        else "Not Loaded"
    )

    print(
        "Perenual API Key:",
        "Loaded"
        if PERENUAL_API_KEY
        else "Not Loaded"
    )

    print(
        "Open-Meteo API:",
        "Ready"
    )

    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
    