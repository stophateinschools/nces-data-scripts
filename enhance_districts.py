import csv
import sys
import typing as t
from dataclasses import dataclass

import click
import httpx
from bs4 import BeautifulSoup, Tag

DISTRICT_URL_FMT = "https://nces.ed.gov/ccd/districtsearch/district_detail.asp?Search=1&details=1&ID2={district_id}"
DISTRICT_ID_COLUMN = "NCES District ID"
WEBSITE_COLUMN = "Web"


# The NCES website has a number of columns that are *wrong* -- they claim
# to be the physical address of the district, but in fact are not.
BAD_ADDRESS_STREET_COLUMN = "Street Address"
BAD_ADDRESS_CITY_COLUMN = "City"
BAD_ADDRESS_STATE_COLUMN = "State"
BAD_ADDRESS_ZIP_COLUMN = "ZIP"
BAD_ADDRESS_ZIP4_COLUMN = "ZIP 4-digit"

GOOD_PHYSICAL_STREET_COLUMN = "Physical Street Address"
GOOD_PHYSICAL_CITY_COLUMN = "Physical City"
GOOD_PHYSICAL_STATE_COLUMN = "Physical State"
GOOD_PHYSICAL_ZIP_COLUMN = "Physical ZIP"
GOOD_PHYSICAL_ZIP4_COLUMN = "Physical ZIP 4-digit"

GOOD_MAILING_STREET_COLUMN = "Mailing Street Address"
GOOD_MAILING_CITY_COLUMN = "Mailing City"
GOOD_MAILING_STATE_COLUMN = "Mailing State"
GOOD_MAILING_ZIP_COLUMN = "Mailing ZIP"
GOOD_MAILING_ZIP4_COLUMN = "Mailing ZIP 4-digit"


@click.group()
def main():
    pass


def get_named_span(soup: BeautifulSoup, name: str) -> Tag:
    # Find all spans and look for the one containing the given name
    for span in soup.find_all("span"):
        if span.get_text(strip=True) == f"{name}:":
            return span
    raise ValueError(f"Span with name '{name}' not found")


def get_website_url(soup: BeautifulSoup) -> str:
    span = get_named_span(soup, "Website")
    link = span.find_next("a")
    assert isinstance(link, Tag)
    href = link.get("href", "")
    transfer = str(href) if href else ""
    if transfer.startswith("/transfer.asp?location="):
        href = transfer.split("location=")[1]
        return f"https://{href}/"
    return transfer


@dataclass(frozen=True)
class Address:
    street: str
    city: str
    state: str
    zip: str
    zip4: str

    @classmethod
    def from_string(cls, address_str: str) -> "Address":
        """
        Converts an address of the following form:

        "17500 Mana RD., Apple Valley CA, 92307 –2181"

        That is:

        "Street, City ST, ZIP -ZIP4"
        """
        parts = [part.strip() for part in address_str.split(",")]
        assert len(parts) == 3, f"Unexpected address format: {address_str}"
        street = parts[0]
        splits = None
        try:
            splits = parts[1].rsplit(" ", 1)
            city = splits[0]
            state = splits[1]
        except IndexError:
            raise ValueError(
                f"Unexpected city/state format: '{parts[1]}' with {splits}"
            )
        zip_parts = parts[2].split("–")
        assert len(zip_parts) == 2, f"Unexpected ZIP format: {parts[2]}"
        zip_code = zip_parts[0].strip()
        zip4 = zip_parts[1].strip()
        return cls(street=street, city=city, state=state, zip=zip_code, zip4=zip4)


def get_address_str(soup: BeautifulSoup, name: str) -> str:
    span = get_named_span(soup, name)
    # Collect the next span siblings for address components
    address_parts = []
    for sibling in span.next_siblings:
        if isinstance(sibling, Tag) and sibling.name == "span":
            text = sibling.get_text(strip=True)
            if text:
                address_parts.append(text.replace("\xa0", " ").strip())
    return ", ".join(address_parts)


def get_mailing_address(soup: BeautifulSoup) -> Address:
    address_str = get_address_str(soup, "Mailing Address")
    return Address.from_string(address_str)


def get_physical_address(soup: BeautifulSoup) -> Address:
    address_str = get_address_str(soup, "Physical Address")
    return Address.from_string(address_str)


@main.command()
@click.argument("input_csv", type=click.File("r", encoding="utf-8"))
def web(input_csv: t.IO[str]):
    """
    Enhances a CSV file of school districts by scraping the NCES website
    for each district's website URL and mailing address, adding these as new columns.
    """
    csv_reader = csv.DictReader(input_csv)
    fieldnames = (list(csv_reader.fieldnames or [])) + [
        WEBSITE_COLUMN,
        GOOD_MAILING_STATE_COLUMN,
        GOOD_MAILING_STREET_COLUMN,
        GOOD_MAILING_CITY_COLUMN,
        GOOD_MAILING_ZIP_COLUMN,
        GOOD_MAILING_ZIP4_COLUMN,
        GOOD_PHYSICAL_CITY_COLUMN,
        GOOD_PHYSICAL_STATE_COLUMN,
        GOOD_PHYSICAL_STREET_COLUMN,
        GOOD_PHYSICAL_ZIP_COLUMN,
        GOOD_PHYSICAL_ZIP4_COLUMN,
    ]
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    csv_writer.writeheader()

    for district in csv_reader:
        district_id = "unknown"
        try:
            district_id = district[DISTRICT_ID_COLUMN]
            response = httpx.get(DISTRICT_URL_FMT.format(district_id=district_id))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            district[WEBSITE_COLUMN] = get_website_url(soup)
            mailing_address = get_mailing_address(soup)
            district[GOOD_MAILING_STREET_COLUMN] = mailing_address.street
            district[GOOD_MAILING_CITY_COLUMN] = mailing_address.city
            district[GOOD_MAILING_STATE_COLUMN] = mailing_address.state
            district[GOOD_MAILING_ZIP_COLUMN] = mailing_address.zip
            district[GOOD_MAILING_ZIP4_COLUMN] = mailing_address.zip4
            pa_str = get_address_str(soup, "Physical Address")
            physical_address = get_physical_address(soup)
            district[GOOD_PHYSICAL_STREET_COLUMN] = physical_address.street
            district[GOOD_PHYSICAL_CITY_COLUMN] = physical_address.city
            district[GOOD_PHYSICAL_STATE_COLUMN] = physical_address.state
            district[GOOD_PHYSICAL_ZIP_COLUMN] = physical_address.zip
            district[GOOD_PHYSICAL_ZIP4_COLUMN] = physical_address.zip4
            csv_writer.writerow(district)
            sys.stdout.flush()
        except Exception:
            print(f"Error processing district ID {district_id}", file=sys.stderr)
            print(district, file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
