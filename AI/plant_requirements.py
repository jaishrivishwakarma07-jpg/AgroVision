
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# AgroVision project root
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_FILE, override=False)

API_KEY = os.getenv("PERENUAL_API_KEY", "").strip()
BASE_URL = "https://perenual.com/api/v2"
TIMEOUT = 15
NOT_AVAILABLE = "Not Available"


def empty_profile():
    return {
        "scientific_name": NOT_AVAILABLE,
        "common_name": NOT_AVAILABLE,
        "family": NOT_AVAILABLE,
        "genus": NOT_AVAILABLE,
        "type": NOT_AVAILABLE,
        "cycle": NOT_AVAILABLE,
        "temperature_min": NOT_AVAILABLE,
        "temperature_max": NOT_AVAILABLE,
        "water_requirement": NOT_AVAILABLE,
        "water_benchmark": NOT_AVAILABLE,
        "soil_type": NOT_AVAILABLE,
        "ph_min": NOT_AVAILABLE,
        "ph_max": NOT_AVAILABLE,
        "sunlight": NOT_AVAILABLE,
        "sunlight_min_hours": NOT_AVAILABLE,
        "sunlight_max_hours": NOT_AVAILABLE,
        "humidity": NOT_AVAILABLE,
        "soil_moisture": NOT_AVAILABLE,
        "wind_tolerance": NOT_AVAILABLE,
        "rainfall": NOT_AVAILABLE,
        "growing_season": NOT_AVAILABLE,
        "growth_stages": NOT_AVAILABLE,
        "irrigation": NOT_AVAILABLE,
        "crop_kc": NOT_AVAILABLE,
        "hardiness_min": NOT_AVAILABLE,
        "hardiness_max": NOT_AVAILABLE,
        "source": NOT_AVAILABLE,
        "data_status": "Incomplete",
        "api_status": NOT_AVAILABLE,
    }


def normalize_name(name):
    if isinstance(name, list):
        name = name[0] if name else ""

    return " ".join(str(name or "").strip().lower().split())


def readable(value):
    if value is None or value == "":
        return NOT_AVAILABLE

    if isinstance(value, list):
        values = [readable(item) for item in value]
        values = [v for v in values if v != NOT_AVAILABLE]
        return ", ".join(values) if values else NOT_AVAILABLE

    if isinstance(value, dict):
        parts = [
            f"{key}: {item}"
            for key, item in value.items()
            if item is not None and item != ""
        ]
        return ", ".join(parts) if parts else NOT_AVAILABLE

    return str(value)


def first_available(*values):
    for value in values:
        result = readable(value)

        if result != NOT_AVAILABLE:
            return result

    return NOT_AVAILABLE


def fetch_json(endpoint, params=None):
    """Fetch data and return a readable API status."""
    if not API_KEY:
        return None, "PERENUAL_API_KEY is not configured"

    request_params = dict(params or {})
    request_params["key"] = API_KEY

    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint.lstrip('/')}",
            params=request_params,
            timeout=TIMEOUT,
        )

        if response.status_code == 401:
            return None, "API key is invalid or unauthorized"

        if response.status_code == 403:
            return None, "API access is restricted by the provider"

        if response.status_code == 429:
            # The provider may use this response for a plan restriction.
            message = response.text.strip()

            if "upgrade plan" in message.lower():
                return None, (
                    "Details endpoint requires a plan upgrade. "
                    "Using available species-list data."
                )

            return None, "API rate limit reached"

        if response.status_code == 404:
            return None, "Requested plant data was not found"

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            return None, "Unexpected API response format"

        if data.get("error"):
            return None, str(data["error"])

        return data, "Success"

    except requests.Timeout:
        return None, "API request timed out"

    except requests.RequestException as error:
        return None, f"API request failed: {error}"

    except ValueError:
        return None, "API returned invalid JSON"


def search_species(plant_name):
    """Search and select the closest exact species match."""
    data, message = fetch_json(
        "species-list/",
        {"q": plant_name},
    )

    if not data:
        return None, message

    results = data.get("data", [])

    if not isinstance(results, list) or not results:
        return None, "Species not found in API results"

    requested = normalize_name(plant_name)

    # Prefer an exact common-name match.
    exact_common = [
        item for item in results
        if normalize_name(item.get("common_name")) == requested
    ]

    if exact_common:
        # Avoid selecting a tomato cultivar when the main species exists.
        for item in exact_common:
            scientific_names = item.get("scientific_name", [])

            if not isinstance(scientific_names, list):
                scientific_names = [scientific_names]

            if any(
                normalize_name(name) == "solanum lycopersicum"
                for name in scientific_names
            ):
                return item, "Exact common-name and scientific-name match"

        return exact_common[0], "Exact common-name match"

    # Exact scientific-name match.
    for item in results:
        scientific_names = item.get("scientific_name", [])

        if not isinstance(scientific_names, list):
            scientific_names = [scientific_names]

        if any(
            normalize_name(name) == requested
            for name in scientific_names
        ):
            return item, "Exact scientific-name match"

    # Alternate names, when supplied by the API.
    for item in results:
        other_names = item.get("other_name", [])

        if not isinstance(other_names, list):
            other_names = [other_names]

        if any(
            normalize_name(name) == requested
            for name in other_names
        ):
            return item, "Exact alternate-name match"

    return None, "No exact species match found"


def get_species_details(species_id):
    if not species_id:
        return None, "Species ID is missing"

    return fetch_json(f"species/details/{species_id}/")


def get_plant_requirements(plant_name):
    profile = empty_profile()

    if not str(plant_name or "").strip():
        profile["api_status"] = "Plant name is required"
        return profile

    # First use the endpoint that is currently working.
    species, search_status = search_species(plant_name)

    if not species:
        profile["source"] = "Perenual API"
        profile["api_status"] = search_status
        return profile

    # Populate only values actually supplied by species-list.
    profile["scientific_name"] = first_available(
        species.get("scientific_name")
    )
    profile["common_name"] = first_available(
        species.get("common_name")
    )
    profile["family"] = first_available(
        species.get("family")
    )
    profile["genus"] = first_available(
        species.get("genus")
    )
    profile["type"] = first_available(
        species.get("type")
    )
    profile["cycle"] = first_available(
        species.get("cycle")
    )

    # Try detailed data. If the plan blocks it, keep the list data.
    details, details_status = get_species_details(species.get("id"))

    if details:
        profile["scientific_name"] = first_available(
            details.get("scientific_name"),
            species.get("scientific_name"),
        )
        profile["common_name"] = first_available(
            details.get("common_name"),
            species.get("common_name"),
        )
        profile["family"] = first_available(
            details.get("family"),
            species.get("family"),
        )
        profile["genus"] = first_available(
            details.get("genus"),
            species.get("genus"),
        )
        profile["type"] = first_available(
            details.get("type"),
            species.get("type"),
        )
        profile["cycle"] = first_available(
            details.get("cycle"),
            species.get("cycle"),
        )

        profile["water_requirement"] = first_available(
            details.get("watering"),
            species.get("watering"),
        )
        profile["water_benchmark"] = readable(
            details.get("watering_general_benchmark")
        )
        profile["soil_type"] = readable(details.get("soil"))
        profile["sunlight"] = first_available(
            details.get("sunlight"),
            species.get("sunlight"),
        )

        hardiness = details.get("hardiness") or {}

        if isinstance(hardiness, dict):
            profile["hardiness_min"] = first_available(
                hardiness.get("min")
            )
            profile["hardiness_max"] = first_available(
                hardiness.get("max")
            )

        # Use optional fields only if the API supplies them.
        temperature = details.get("xTemperatureTolerance")

        if isinstance(temperature, dict):
            profile["temperature_min"] = first_available(
                temperature.get("min")
            )
            profile["temperature_max"] = first_available(
                temperature.get("max")
            )

        ph_data = details.get("xWateringPhLevel Supreme User ") or {}

        if isinstance(ph_data, dict):
            profile["ph_min"] = first_available(ph_data.get("min"))
            profile["ph_max"] = first_available(ph_data.get("max"))

        sunlight_data = (
            details.get("xSunlightDuration Supreme User ") or {}
        )

        if isinstance(sunlight_data, dict):
            unit = sunlight_data.get("unit", "hours")
            minimum = sunlight_data.get("min")
            maximum = sunlight_data.get("max")

            if minimum is not None:
                profile["sunlight_min_hours"] = f"{minimum} {unit}"

            if maximum is not None:
                profile["sunlight_max_hours"] = f"{maximum} {unit}"

        profile["humidity"] = first_available(
            details.get("humidity"),
            details.get("xHumidity"),
        )
        profile["soil_moisture"] = first_available(
            details.get("soil_moisture"),
            details.get("xSoilMoisture"),
        )
        profile["wind_tolerance"] = first_available(
            details.get("wind_tolerance"),
            details.get("xWindTolerance"),
        )
        profile["rainfall"] = first_available(
            details.get("rainfall"),
            details.get("xRainfall"),
        )
        profile["growing_season"] = first_available(
            details.get("growing_season"),
            details.get("flowering_season"),
            details.get("harvest_season"),
        )
        profile["growth_stages"] = readable(
            details.get("growth_stages")
        )
        profile["irrigation"] = first_available(
            details.get("irrigation"),
            details.get("watering"),
        )
        profile["crop_kc"] = first_available(
            details.get("crop_kc"),
            details.get("kc"),
        )

        profile["source"] = (
            "Perenual API: species-list + species/details"
        )
        profile["api_status"] = f"{search_status}; {details_status}"

    else:
        # Do not retry the restricted endpoint or invent missing values.
        profile["source"] = "Perenual API: species-list only"
        profile["api_status"] = (
            f"{search_status}; details unavailable: {details_status}"
        )

    essential_fields = [
        "scientific_name",
        "common_name",
        "family",
    ]

    available_count = sum(
        profile[key] != NOT_AVAILABLE
        for key in essential_fields
    )

    if details and available_count == len(essential_fields):
        profile["data_status"] = "Plant details retrieved"
    elif available_count:
        profile["data_status"] = (
            "Basic plant information available; "
            "growing requirements are incomplete"
        )
    else:
        profile["data_status"] = "Incomplete"

    return profile


def display_profile(profile):
    print("\n" + "=" * 62)
    print("AGROVISION - PLANT REQUIREMENT DATA")
    print("=" * 62)

    sections = {
        "PLANT INFORMATION": [
            ("Scientific Name", "scientific_name"),
            ("Common Name", "common_name"),
            ("Family", "family"),
            ("Genus", "genus"),
            ("Type", "type"),
            ("Cycle", "cycle"),
        ],
        "TEMPERATURE": [
            ("Minimum", "temperature_min"),
            ("Maximum", "temperature_max"),
        ],
        "WATER": [
            ("Requirement", "water_requirement"),
            ("Benchmark", "water_benchmark"),
            ("Irrigation", "irrigation"),
        ],
        "SOIL": [
            ("Soil Type", "soil_type"),
            ("Minimum pH", "ph_min"),
            ("Maximum pH", "ph_max"),
            ("Soil Moisture", "soil_moisture"),
        ],
        "SUNLIGHT": [
            ("Requirement", "sunlight"),
            ("Minimum Hours", "sunlight_min_hours"),
            ("Maximum Hours", "sunlight_max_hours"),
        ],
        "OTHER REQUIREMENTS": [
            ("Humidity", "humidity"),
            ("Wind Tolerance", "wind_tolerance"),
            ("Rainfall", "rainfall"),
            ("Growing Season", "growing_season"),
            ("Growth Stages", "growth_stages"),
            ("Crop Kc", "crop_kc"),
        ],
        "HARDINESS": [
            ("Minimum Zone", "hardiness_min"),
            ("Maximum Zone", "hardiness_max"),
        ],
    }

    for section, fields in sections.items():
        print(f"\n{section}")
        print("-" * 62)

        for label, key in fields:
            print(f"{label:<22}: {profile.get(key, NOT_AVAILABLE)}")

    print("\nDATA SOURCE & STATUS")
    print("-" * 62)
    print("Source      :", profile.get("source", NOT_AVAILABLE))
    print("Data status :", profile.get("data_status", "Incomplete"))
    print("API status  :", profile.get("api_status", NOT_AVAILABLE))
    print("=" * 62)


def main():
    print("\nAGROVISION")
    print("Plant Requirement API Test")
    print("-" * 62)

    plant_name = input(
        "Enter Plant Name (Example: Tomato): "
    ).strip()

    if not plant_name:
        print("Plant name cannot be empty.")
        return

    print("\nFetching plant information...")
    profile = get_plant_requirements(plant_name)
    display_profile(profile)

    print("\nAgroVision plant requirement test completed.")


if __name__ == "__main__":
    main()
