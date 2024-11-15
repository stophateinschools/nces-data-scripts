import csv
import sys

import click


@click.command()
@click.argument("input_csv", type=click.File("r"))
def extract_school_info(input_csv):
    """
    Extract school information from a geocoded CSV and output it as a CSV with specified columns:
    School-Name, School-Type, District, School-Level, Address, Latitude, Longitude.
    """
    csv_reader = csv.DictReader(input_csv)
    fieldnames = [
        "NCES-School-ID",
        "School-Name",
        "School-Type",
        "NCES-District-ID",
        "District",
        "School-Level",
        "Address",
        "Phone",
        "Latitude",
        "Longitude",
    ]
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

    # Write the header
    csv_writer.writeheader()

    seen_schools = set()

    # Process each row and extract relevant information
    for row in csv_reader:
        school_id = row["NCES School ID"]
        if school_id in seen_schools:
            continue
        seen_schools.add(school_id)
        school_level = determine_school_level(row["Low Grade*"], row["High Grade*"])
        address = f"{row['Street Address']}, {row['City']}, {row['State']} {row['ZIP']}"

        school_info = {
            "NCES-School-ID": school_id,
            "School-Name": row["School Name"],  # Adjust column name if necessary
            "School-Type": "Public",
            "NCES-District-ID": row["NCES District ID"],
            "District": row["District"],  # Adjust column name if necessary
            "School-Level": school_level,
            "Address": address,
            "Phone": row["Phone"],
            "Latitude": row["Latitude"],
            "Longitude": row["Longitude"],
        }
        csv_writer.writerow(school_info)


def determine_school_level(low_grade, high_grade):
    """
    Determine the school level based on the low and high grades.
    Returns a comma-separated list of 'Elementary', 'Middle', 'High'.
    """
    levels = []

    # Map grade ranges to school levels
    if high_grade in {"PK"}:
        levels.append("Pre-K")

    if low_grade in {"KG", "01", "02", "03", "04", "05"} or high_grade in {
        "KG",
        "01",
        "02",
        "03",
        "04",
        "05",
    }:
        levels.append("Elementary")

    if low_grade in {"06", "07", "08"} or high_grade in {"07", "08"}:
        levels.append("Middle")

    if low_grade in {"09", "10", "11", "12"} or high_grade in {"09", "10", "11", "12"}:
        levels.append("High")

    return ",".join(levels)


if __name__ == "__main__":
    extract_school_info()
