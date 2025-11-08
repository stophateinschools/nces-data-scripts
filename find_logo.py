import csv
import sys
import typing as t
from io import BytesIO

import click
import httpx
from bs4 import BeautifulSoup
from PIL import Image

WEBSITE_COLUMN = "Web"
LOGO_URL_COLUMN = "Logo URL"


def get_image_size(url: str) -> tuple[int, int]:
    """
    Retrieve the image from the given URL and return its dimensions (width, height).
    """
    response = httpx.get(url, follow_redirects=True, timeout=10.0)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content))
    return image.size  # (width, height)


def find_logo_urls(soup: BeautifulSoup) -> t.Iterable[tuple[str, tuple[int, int]]]:
    """
    Make several attempts to find a logo image URL from the given webpage:

    1. Any <img> tag with class "logo", or where the "alt" attribute contains "logo",
       or where the URL itself contains "logo" once lowered.
    2. Any <link> tag with rel="icon" or rel="shortcut icon".

    For each found image URL, retrieve its dimensions and yield a tuple of (URL, (width, height)).
    """
    # Attempt 1: Look for <img> tags
    for img in soup.find_all("img"):
        img_url = img.get("src", "")
        if not isinstance(img_url, str) or not img_url:
            continue
        img_url_lower = img_url.lower()
        alt_text = img.get("alt", "")
        if not isinstance(alt_text, str):
            alt_text = ""
        else:
            alt_text = alt_text.lower()
        if "logo" in alt_text or "logo" in img_url_lower or "brand" in img_url_lower:
            try:
                size = get_image_size(img_url)
                yield (img_url, size)
            except httpx.HTTPError:
                continue

    # Attempt 2: Look for <link> tags with rel="icon" or rel="shortcut icon"
    for link in soup.find_all("link", rel=["icon", "shortcut icon"]):
        icon_url = link.get("href", "")
        if not isinstance(icon_url, str) or not icon_url:
            continue
        try:
            size = get_image_size(icon_url)
            yield (icon_url, size)
        except httpx.HTTPError:
            continue


def find_best_logo_url(soup: BeautifulSoup) -> str:
    """
    Find the best logo URL from the given webpage soup.

    The "best" logo is defined as the one with the largest area (width * height).
    If no logos are found, return an empty string.
    """
    best_logo_url = ""
    best_area = 0
    for logo_url, (width, height) in find_logo_urls(soup):
        area = width * height
        if area > best_area:
            best_area = area
            best_logo_url = logo_url
    return best_logo_url


@click.command()
@click.argument("input_csv", type=click.File("r", encoding="utf-8"))
def find_logo(input_csv: t.IO[str]) -> None:
    csv_reader = csv.DictReader(input_csv)
    fieldnames = list(csv_reader.fieldnames or []) + [LOGO_URL_COLUMN]
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    csv_writer.writeheader()

    for district in csv_reader:
        website_url = district.get(WEBSITE_COLUMN, "")
        logo_url = ""
        if website_url:
            try:
                response = httpx.get(website_url, follow_redirects=True, timeout=10.0)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                logo_url = find_best_logo_url(soup)
            except Exception:
                logo_url = ""
        district[LOGO_URL_COLUMN] = logo_url
        csv_writer.writerow(district)
        sys.stdout.flush()
