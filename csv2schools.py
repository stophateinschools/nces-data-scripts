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
        "School-Name",
        "School-Type",
        "District",
        "School-Level",
        "Address",
        "Latitude",
        "Longitude",
    ]
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

    # Write the header
    csv_writer.writeheader()

    # Process each row and extract relevant information
    for row in csv_reader:
        school_level = determine_school_level(row["Low Grade*"], row["High Grade*"])
        address = f"{row['Street Address']}, {row['City']}, {row['State']} {row['ZIP']}"

        school_info = {
            "School-Name": row["School Name"],  # Adjust column name if necessary
            "School-Type": "Public",
            "District": row["District"],  # Adjust column name if necessary
            "School-Level": school_level,
            "Address": address,
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
    if low_grade in ["PK", "KG", "01", "02", "03", "04", "05"] or high_grade in [
        "PK",
        "KG",
        "01",
        "02",
        "03",
        "04",
        "05",
    ]:
        levels.append("Elementary")

    if low_grade in ["06", "07", "08"] or high_grade in ["06", "07", "08"]:
        levels.append("Middle")

    if low_grade in ["09", "10", "11", "12"] or high_grade in ["09", "10", "11", "12"]:
        levels.append("High")

    return ", ".join(levels)


if __name__ == "__main__":
    extract_school_info()
