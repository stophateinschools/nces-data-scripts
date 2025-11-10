"""
Converts an HTML file containing a table of public schools or districts
to CSV and writes to stdout.

See the README for usage instructions.
"""

import csv
import sys

import click
from bs4 import BeautifulSoup, Tag


@click.command()
@click.argument("html_file", type=click.File("r", encoding="windows-1252"))
def convert_html_to_csv(html_file):
    """
    Converts an HTML file containing a table of public schools to CSV and writes to stdout.
    """
    # Parse the HTML
    soup = BeautifulSoup(html_file, "html.parser")

    # Find the table in the HTML
    table = soup.find("table")

    # Prepare CSV writer to emit to stdout
    csvwriter = csv.writer(sys.stdout)

    # Find the row that contains headers and write it
    headers_written = False
    assert isinstance(table, Tag)
    for row in table.find_all("tr"):
        headers = [cell.text.strip() for cell in row.find_all("td")]
        if headers and (
            "NCES School ID" in headers[0] or "NCES District ID" in headers[0]
        ):  # The row with 'NCES School ID' marks the start of the headers
            csvwriter.writerow(headers)
            headers_written = True
            break

    # Write the remaining rows after headers
    if headers_written:
        for row in table.find_all("tr")[table.find_all("tr").index(row) + 1 :]:
            cells = [cell.text.strip() for cell in row.find_all("td")]
            if cells:  # Skip empty rows
                csvwriter.writerow(cells)


if __name__ == "__main__":
    convert_html_to_csv()
