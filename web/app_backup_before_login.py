import sys
import os
import json
import base64
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv


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
def dashboard_page():

    farmers = dashboard_records("farmers.json")
    farms = dashboard_records("farms.json")
    crops = dashboard_records("crops.json")
    soil = dashboard_records("soil.json")
    irrigation = dashboard_records("irrigation.json")
    weather = dashboard_records("weather.json")
    diseases = dashboard_records("disease.json")
    fertilizer = dashboard_records("fertilizer.json")

    crop_status = Counter(
        dashboard_value(item, "status")
        for item in crops
    )

    crop_seasons = Counter(
        dashboard_value(item, "season")
        for item in crops
    )

    districts = Counter(
        dashboard_value(item, "district")
        for item in farms
    )

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

    latest_soil = None

    if soil:
        item = soil[-1]
        latest_soil = {
            "soil_type": dashboard_value(item, "soil_type"),
            "ph": dashboard_value(item, "ph"),
            "nitrogen": dashboard_value(item, "nitrogen"),
            "phosphorus": dashboard_value(item, "phosphorus"),
            "potassium": dashboard_value(item, "potassium"),
            "moisture": dashboard_value(item, "moisture"),
        }

    latest_weather = None

    if weather:
        item = weather[-1]
        latest_weather = {
            "city": dashboard_value(item, "city"),
            "temperature": dashboard_value(item, "temperature"),
            "humidity": dashboard_value(item, "humidity"),
            "rain": dashboard_value(item, "rain"),
            "wind": dashboard_value(item, "wind"),
            "condition": dashboard_value(item, "condition"),
        }

    recent_diseases = []

    # Show the latest 8 records first.
    for item in reversed(diseases[-8:]):
        timestamp = dashboard_value(item, "timestamp")
        date = timestamp[:10] if timestamp != "Unknown" else "Unknown"

        confidence = item.get("confidence", "Unknown")

        if confidence is not None:
            try:
                confidence = round(float(confidence), 2)
            except (TypeError, ValueError):
                confidence = "Unknown"

        recent_diseases.append({
            "disease": dashboard_value(item, "disease"),
            "confidence": confidence,
            "date": date,
        })

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
    
    
   