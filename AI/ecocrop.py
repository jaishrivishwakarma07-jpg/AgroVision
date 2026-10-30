
import csv
import os
import re
import sys
from difflib import SequenceMatcher

# ============================================================
# AGROVISION - ECOCROP SEARCH WITH SAFE MATCHING
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATASET_PATHS = [
    os.path.join(PROJECT_ROOT, "datasets", "EcoCrop_DB.csv"),
    os.path.join(PROJECT_ROOT, "database", "EcoCrop_DB.csv"),
    os.path.join(PROJECT_ROOT, "datasets", "EcoCrop_DB (5).csv"),
    os.path.join(PROJECT_ROOT, "datasets", "EcoCrop_DB (1).csv"),
]


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_column(value):
    if value is None:
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).strip().lower()
    )


def clean_value(value):
    if value is None:
        return ""

    value = str(value).strip()

    if value.lower() in {
        "", "nan", "none", "null", "n/a", "na", "-"
    }:
        return ""

    return value


def get_value(row, *names):
    for name in names:
        value = clean_value(
            row.get(normalize_column(name), "")
        )

        if value:
            return value

    return ""


# ============================================================
# DATASET LOADING
# ============================================================

def find_dataset():
    for path in DATASET_PATHS:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return path

    return None


def load_ecocrop_dataset(path):
    """
    Load the CSV using the actual headers, including:
    ScientificName, COMNAME, SYNO, TMIN, TMAX,
    RMIN, RMAX, PHMIN and PHMAX.
    """

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin-1",
    ]

    last_error = None

    for encoding in encodings:
        try:
            with open(
                path,
                "r",
                encoding=encoding,
                newline=""
            ) as file:

                sample = file.read(20000)
                file.seek(0)

                if not sample.strip():
                    raise ValueError("The CSV file is empty.")

                try:
                    dialect = csv.Sniffer().sniff(
                        sample,
                        delimiters=",;\t|"
                    )
                except csv.Error:
                    dialect = csv.excel

                reader = csv.DictReader(
                    file,
                    dialect=dialect
                )

                if not reader.fieldnames:
                    raise ValueError("CSV headers are missing.")

                header_map = {
                    normalize_column(header): header
                    for header in reader.fieldnames
                    if header
                }

                rows = []

                for original_row in reader:
                    row = {}

                    for normalized_header, original_header in (
                        header_map.items()
                    ):
                        row[normalized_header] = (
                            original_row.get(original_header, "")
                        )

                    if any(clean_value(v) for v in row.values()):
                        rows.append(row)

                if not rows:
                    raise ValueError("No data records found.")

                return rows, header_map

        except (
            OSError,
            UnicodeError,
            csv.Error,
            ValueError
        ) as error:
            last_error = error

    raise RuntimeError(
        f"Could not read the EcoCrop CSV: {last_error}"
    )


# ============================================================
# MATCHING
# ============================================================

def split_synonyms(value):
    """
    Split synonym fields into individual names.
    Supports common delimiters.
    """
    if not value:
        return []

    parts = re.split(r"[;|]", value)

    return [
        part.strip()
        for part in parts
        if part.strip()
    ]


def plant_names(row):
    scientific = get_value(
        row, "ScientificName", "Scientific Name"
    )

    common = get_value(
        row, "COMNAME", "CommonName", "Common Name"
    )

    synonyms = get_value(
        row, "SYNO", "Synonym", "Synonyms"
    )

    return {
        "scientific": scientific,
        "common": common,
        "synonyms": split_synonyms(synonyms),
    }


def search_plants(rows, query, limit=8):
    """
    Matching order:
    1. Exact scientific name
    2. Exact common name
    3. Exact synonym
    4. Partial matches for suggestions only

    Partial matches are never treated as verified matches.
    """

    query_normalized = normalize_text(query)

    if not query_normalized:
        return {
            "status": "empty_query",
            "exact_type": None,
            "matches": [],
            "suggestions": [],
        }

    scientific_matches = []
    common_matches = []
    synonym_matches = []
    suggestions = []

    for row in rows:
        names = plant_names(row)

        scientific = normalize_text(names["scientific"])
        common = normalize_text(names["common"])

        synonyms = [
            normalize_text(name)
            for name in names["synonyms"]
        ]

        if scientific and scientific == query_normalized:
            scientific_matches.append(row)
            continue

        if common and common == query_normalized:
            common_matches.append(row)
            continue

        if query_normalized in synonyms:
            synonym_matches.append(row)
            continue

        # Similar names are only suggestions.
        candidate_names = [
            names["scientific"],
            names["common"],
            *names["synonyms"],
        ]

        best_score = 0.0

        for candidate in candidate_names:
            candidate_normalized = normalize_text(candidate)

            if not candidate_normalized:
                continue

            score = SequenceMatcher(
                None,
                query_normalized,
                candidate_normalized
            ).ratio()

            if query_normalized in candidate_normalized:
                score = max(score, 0.80)

            best_score = max(best_score, score)

        if best_score >= 0.55:
            suggestions.append({
                "row": row,
                "score": best_score,
            })

    if scientific_matches:
        return {
            "status": "exact_match",
            "exact_type": "scientific_name",
            "matches": scientific_matches[:limit],
            "suggestions": [],
        }

    if common_matches:
        return {
            "status": "exact_match",
            "exact_type": "common_name",
            "matches": common_matches[:limit],
            "suggestions": [],
        }

    if synonym_matches:
        return {
            "status": "exact_match",
            "exact_type": "synonym",
            "matches": synonym_matches[:limit],
            "suggestions": [],
        }

    suggestions.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return {
        "status": "no_exact_match",
        "exact_type": None,
        "matches": [],
        "suggestions": suggestions[:limit],
    }


# ============================================================
# REQUIREMENT PROFILE
# ============================================================

def build_profile(row):
    return {
        "ecocrop_code": get_value(
            row, "EcoPortCode", "EcoCropCode", "Code"
        ),

        "scientific_name": get_value(
            row, "ScientificName", "Scientific Name"
        ),

        "common_name": get_value(
            row, "COMNAME", "CommonName", "Common Name"
        ),

        "family": get_value(
            row, "FAMNAME", "Family", "FamilyName"
        ),

        "synonyms": get_value(
            row, "SYNO", "Synonym", "Synonyms"
        ),

        "minimum_temperature": get_value(
            row, "TMIN"
        ),

        "maximum_temperature": get_value(
            row, "TMAX"
        ),

        "optimal_temperature_min": get_value(
            row, "TOPMN"
        ),

        "optimal_temperature_max": get_value(
            row, "TOPMX"
        ),

        "minimum_rainfall": get_value(
            row, "RMIN"
        ),

        "maximum_rainfall": get_value(
            row, "RMAX"
        ),

        "optimal_rainfall_min": get_value(
            row, "ROPMN"
        ),

        "optimal_rainfall_max": get_value(
            row, "ROPMX"
        ),

        "minimum_ph": get_value(
            row, "PHMIN"
        ),

        "maximum_ph": get_value(
            row, "PHMAX"
        ),

        "soil_texture": get_value(
            row, "TEXT", "SoilTexture"
        ),

        "soil_depth": get_value(
            row, "DEP", "SoilDepth"
        ),

        "soil_fertility": get_value(
            row, "FERT", "SoilFertility"
        ),

        "soil_drainage": get_value(
            row, "DRAIN", "SoilDrainage"
        ),

        "climate_zone": get_value(
            row, "CLIZ", "ClimateZone"
        ),

        "life_form": get_value(
            row, "LIFO", "LifeForm"
        ),

        "plant_habit": get_value(
            row, "HABIT", "Habit"
        ),

        "light": get_value(
            row, "LIGHT", "Light"
        ),

        "growth_cycle_min": get_value(
            row, "GMIN"
        ),

        "growth_cycle_max": get_value(
            row, "GMAX"
        ),
    }


# ============================================================
# DISPLAY
# ============================================================

def show_value(label, value, unit=""):
    value = clean_value(value)

    if not value:
        value = "Not available"
    else:
        value = value + unit

    print(f"{label:<29}: {value}")


def display_profile(profile, match_type):
    print("\n" + "=" * 62)
    print("AGROVISION - ECOCROP PLANT PROFILE")
    print("=" * 62)

    print(f"Match type                    : {match_type}")

    show_value("EcoCrop Code", profile["ecocrop_code"])
    show_value("Scientific Name", profile["scientific_name"])
    show_value("Common Name", profile["common_name"])
    show_value("Family", profile["family"])
    show_value("Synonyms", profile["synonyms"])

    print("\nTEMPERATURE")
    print("-" * 62)

    show_value(
        "Minimum Temperature",
        profile["minimum_temperature"],
        " °C"
    )
    show_value(
        "Maximum Temperature",
        profile["maximum_temperature"],
        " °C"
    )
    show_value(
        "Optimal Temperature Min",
        profile["optimal_temperature_min"],
        " °C"
    )
    show_value(
        "Optimal Temperature Max",
        profile["optimal_temperature_max"],
        " °C"
    )

    print("\nRAINFALL")
    print("-" * 62)

    show_value(
        "Minimum Rainfall",
        profile["minimum_rainfall"],
        " mm"
    )
    show_value(
        "Maximum Rainfall",
        profile["maximum_rainfall"],
        " mm"
    )
    show_value(
        "Optimal Rainfall Min",
        profile["optimal_rainfall_min"],
        " mm"
    )
    show_value(
        "Optimal Rainfall Max",
        profile["optimal_rainfall_max"],
        " mm"
    )

    print("\nSOIL")
    print("-" * 62)

    show_value("Minimum Soil pH", profile["minimum_ph"])
    show_value("Maximum Soil pH", profile["maximum_ph"])
    show_value("Soil Texture", profile["soil_texture"])
    show_value("Soil Depth", profile["soil_depth"])
    show_value("Soil Fertility", profile["soil_fertility"])
    show_value("Soil Drainage", profile["soil_drainage"])

    print("\nCLIMATE AND GROWTH")
    print("-" * 62)

    show_value("Climate Zone", profile["climate_zone"])
    show_value("Light", profile["light"])
    show_value("Life Form", profile["life_form"])
    show_value("Plant Habit", profile["plant_habit"])
    show_value("Growth Cycle Minimum", profile["growth_cycle_min"])
    show_value("Growth Cycle Maximum", profile["growth_cycle_max"])

    print("\nNote: Unavailable values are not guessed.")
    print("Verify dataset field units before agronomic decisions.")
    print("=" * 62)


def main():
    print("\n" + "=" * 62)
    print("AGROVISION - ECOCROP PLANT SEARCH")
    print("=" * 62)

    dataset_path = find_dataset()

    if not dataset_path:
        print("\nERROR: EcoCrop_DB.csv was not found.")
        print(
            "Expected location:",
            os.path.join(PROJECT_ROOT, "datasets", "EcoCrop_DB.csv")
        )
        return

    try:
        rows, header_map = load_ecocrop_dataset(dataset_path)
    except Exception as error:
        print(f"\nDataset loading error: {error}")
        return

    print(f"\nDataset: {os.path.basename(dataset_path)}")
    print(f"Records loaded: {len(rows)}")

    for required in ("scientificname", "comname", "syno"):
        if required in header_map:
            print(f"Column found: {header_map[required]}")

    query = input(
        "\nEnter scientific name or common name: "
    ).strip()

    if not query:
        print("Please enter a plant name.")
        return

    result = search_plants(rows, query)

    if result["status"] == "exact_match":
        matches = result["matches"]

        print(
            f"\nExact match found by: {result['exact_type']}"
        )

        if len(matches) > 1:
            print(f"Matching records: {len(matches)}")

            for index, row in enumerate(matches, start=1):
                name = get_value(
                    row, "ScientificName", "Scientific Name"
                )
                common = get_value(
                    row, "COMNAME", "CommonName", "Common Name"
                )
                print(f"{index}. {name} | {common or 'No common name'}")

            selection = input(
                "Select record number (Enter for first): "
            ).strip()

            if selection.isdigit():
                index = int(selection) - 1
                if 0 <= index < len(matches):
                    selected_row = matches[index]
                else:
                    selected_row = matches[0]
            else:
                selected_row = matches[0]
        else:
            selected_row = matches[0]

        profile = build_profile(selected_row)
        display_profile(profile, result["exact_type"])

    else:
        print("\nNO EXACT MATCH FOUND")
        print(
            f"EcoCrop does not contain an exact name match for: {query}"
        )

        suggestions = result["suggestions"]

        if not suggestions:
            print("No similar names were found.")
            return

        print("\nPossible similar records (suggestions only):")

        for index, item in enumerate(suggestions, start=1):
            profile = build_profile(item["row"])
            print(
                f"{index}. {profile['scientific_name']} "
                f"| {profile['common_name'] or 'No common name'} "
                f"| Similarity: {item['score'] * 100:.1f}%"
            )

        print(
            "\nNo requirements were displayed because an exact "
            "plant-name match was not found."
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram stopped.")
        sys.exit(0)