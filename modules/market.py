
import csv
from pathlib import Path

# AGROVISION Market Price Module
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_FILE = BASE_DIR / "database" / "mandi_prices.csv"


def clean_text(value):
    """Normalize text for case-insensitive searching."""
    return str(value or "").strip().casefold()


def read_market_data():
    """Read mandi prices from the downloaded CSV file."""
    if not CSV_FILE.exists():
        print("\nError: mandi_prices.csv file nahi mili.")
        print(f"Expected location: {CSV_FILE}")
        return []

    try:
        # utf-8-sig handles CSV files containing a BOM.
        with open(CSV_FILE, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            required = {
                "State", "District", "Market", "Commodity",
                "Arrival_Date", "Min_x0020_Price",
                "Max_x0020_Price", "Modal_x0020_Price"
            }

            if not reader.fieldnames:
                print("\nError: CSV file mein column headings nahi hain.")
                return []

            missing = required - set(reader.fieldnames)
            if missing:
                print("\nError: CSV mein required columns missing hain:")
                print(", ".join(sorted(missing)))
                print("CSV headings check karo.")
                return []

            return list(reader)

    except (OSError, UnicodeError, csv.Error) as error:
        print(f"\nCSV read error: {error}")
        return []


def show_prices(rows):
    """Display matching mandi price records."""
    print("\n" + "=" * 78)
    print("              AGROVISION - MANDI MARKET PRICES")
    print("=" * 78)

    for number, row in enumerate(rows, start=1):
        print(f"\nRecord {number}")
        print(f"Crop       : {row.get('Commodity', 'N/A')}")
        print(f"State      : {row.get('State', 'N/A')}")
        print(f"District   : {row.get('District', 'N/A')}")
        print(f"Market     : {row.get('Market', 'N/A')}")
        print(f"Variety    : {row.get('Variety', 'N/A')}")
        print(f"Grade      : {row.get('Grade', 'N/A')}")
        print(f"Arrival Date: {row.get('Arrival_Date', 'N/A')}")
        print(f"Min Price  : Rs. {row.get('Min_x0020_Price', 'N/A')}/quintal")
        print(f"Max Price  : Rs. {row.get('Max_x0020_Price', 'N/A')}/quintal")
        print(f"Modal Price: Rs. {row.get('Modal_x0020_Price', 'N/A')}/quintal")

    print("\n" + "-" * 78)
    print("Source: Downloaded mandi_prices.csv")
    print("Note: Prices are from the CSV; they may not be live/current.")
    print("=" * 78)


def market_price_menu():
    print("\n" + "=" * 48)
    print("       AGROVISION - MARKET PRICE")
    print("=" * 48)

    if not CSV_FILE.exists():
        print("\nMarket data file not found.")
        print(f"Place mandi_prices.csv here: {CSV_FILE}")
        return

    crop = input("Enter crop name (e.g. Wheat): ").strip()
    state = input("Enter state (e.g. Madhya Pradesh): ").strip()
    district = input("Enter district (e.g. Satna, or press Enter for all): ").strip()

    if not crop or not state:
        print("\nCrop name and state are required.")
        return

    print("\nSearching downloaded mandi data...")
    data = read_market_data()

    if not data:
        print("\nNo usable market data found.")
        return

    # Exact crop-name match; partial state/district matches.
    matches = [
        row for row in data
        if clean_text(row.get("Commodity")) == clean_text(crop)
        and clean_text(row.get("State")) == clean_text(state)
        and (
            not district
            or clean_text(district) in clean_text(row.get("District"))
        )
    ]

    if not matches:
        print("\nNo matching records found.")
        print("Check crop spelling, state, and district.")
        print("\nSome crop names in this CSV:")
        crop_names = sorted({
            row.get("Commodity", "").strip()
            for row in data
            if row.get("Commodity", "").strip()
        })
        for name in crop_names[:20]:
            print(" -", name)
        if len(crop_names) > 20:
            print(f"...and {len(crop_names) - 20} more.")
        return

    # Sort by arrival date text; dates are displayed as provided in the CSV.
    show_prices(matches[:50])

    if len(matches) > 50:
        print(f"\nShowing first 50 of {len(matches)} matching records.")


if __name__ == "__main__":
    market_price_menu()
