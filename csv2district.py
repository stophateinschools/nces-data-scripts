import csv
import sys

import click


@click.command()
@click.argument("input_csv", type=click.File("r"))
def extract_district_info(input_csv):
    """
    Extract district information (name and phone) from a geocoded CSV and output it as a CSV with two columns:
    District-Name and District-Phone.
    """
    csv_reader = csv.DictReader(input_csv)
    fieldnames = ["NCES-District-ID", "District-Name", "District-Phone"]
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

    # Write the header
    csv_writer.writeheader()

    # Set to keep track of seen district name and phone tuples
    seen_districts = set()

    # Process each row and extract relevant information
    for row in csv_reader:
        district_id = row["NCES District ID"]

        if district_id not in seen_districts:
            seen_districts.add(district_id)
            district_info = {
                "District-Name": row["District"],
                "District-Phone": row["Phone"],
                "NCES-District-ID": district_id,
            }
            csv_writer.writerow(district_info)


if __name__ == "__main__":
    extract_district_info()
