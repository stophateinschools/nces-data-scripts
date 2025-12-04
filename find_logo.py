"""
find_logo: find school district logos using a variety of heuristics.

This is a big HACK HACK HACK. It could be improved in many ways.

Usage:
    uv run python find_logo.py one https://example-school-district.com
    uv run python find_logo.py all input.csv > output.csv

    # If something goes wrong partway through, you can continue:
    uv run python find_logo.py all-continue input.csv previous_output.csv > output.csv
"""

import csv
import sys
import typing as t
from io import BytesIO
from urllib.parse import urljoin

import click
import httpx
from bs4 import BeautifulSoup
from PIL import Image

WEBSITE_COLUMN = "Web"
LOGO_URL_COLUMN = "Logo URL"

# Sigh. I hate doing this.
ALT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.1 Safari/605.1.15 LogoFinder/0.1"
HEADERS = {
    "User-Agent": ALT_UA,
}


@click.group()
def main():
    pass


class ImageError(Exception):
    """Custom exception for image retrieval errors."""

    pass


def get_image_size(abs_url: str) -> tuple[int, int]:
    """
    Retrieve the image from the given URL and return its dimensions (width, height).
    """
    # Use python's built-in URL stuff to resolve relative URLs
    try:
        response = httpx.get(
            abs_url, follow_redirects=True, timeout=10.0, headers=HEADERS
        )
        response.raise_for_status()
    except Exception as e:
        raise ImageError(f"Error fetching image from {abs_url}: {e}")

    # Is this an image mime type?
    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        raise ImageError(f"URL does not point to an image: {abs_url}")

    try:
        image = Image.open(BytesIO(response.content))
        return image.size  # (width, height)
    except Exception as e:
        raise ImageError(f"Error processing image from {abs_url}: {e}")


def find_logo_urls(
    base_url: str, soup: BeautifulSoup
) -> t.Iterable[tuple[str, tuple[int, int]]]:
    """
    Make several attempts to find a logo image URL from the given webpage:

    1. Any <img> tag with class "logo", or where the "alt" attribute contains "logo",
       or where the URL itself contains "logo" once lowered.
    2. Any <link> tag with rel="icon" or rel="shortcut icon".

    For each found image URL, retrieve its dimensions and yield a tuple of (URL, (width, height)).
    """
    # Attempt 1: Look for <img> tags
    for img in soup.find_all("img"):
        print("CONSIDERING IMG TAG:", img, file=sys.stderr)
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
                img_url = urljoin(base_url, img_url)
                size = get_image_size(img_url)
                yield (img_url, size)
            except ImageError:
                continue

    # Attempt 2: Look for <link> tags with rel="icon" or rel="shortcut icon"
    for link in soup.find_all("link", rel=["icon", "shortcut icon"]):
        icon_url = link.get("href", "")
        if not isinstance(icon_url, str) or not icon_url:
            continue
        try:
            icon_url = urljoin(base_url, icon_url)
            size = get_image_size(icon_url)
            yield (icon_url, size)
        except ImageError:
            continue


def find_best_logo_url(base_url: str, soup: BeautifulSoup) -> str:
    """
    Find the best logo URL from the given webpage soup.

    The "best" logo is defined as the one with the largest area (width * height).
    If no logos are found, return an empty string.
    """
    best_logo_url = ""
    best_area = 0
    for logo_url, (width, height) in find_logo_urls(base_url, soup):
        print("CONSIDERING LOGO:", logo_url, f"({width}x{height})", file=sys.stderr)
        area = width * height
        if area > best_area:
            best_area = area
            best_logo_url = logo_url
    return best_logo_url


def find_best_logo_url_from_site(website_url: str) -> str:
    """
    Fetch the webpage at the given URL and find the best logo URL.

    Or return an empty string if none found or on error.
    """
    try:
        response = httpx.get(
            website_url, follow_redirects=True, timeout=10.0, headers=HEADERS
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return find_best_logo_url(website_url, soup)
    except Exception as e:
        print(f"Error fetching website {website_url}: {e}", file=sys.stderr)
        return ""


@main.command()
@click.argument("input_csv", type=click.File("r", encoding="utf-8"))
def all(input_csv: t.IO[str]) -> None:
    csv_reader = csv.DictReader(input_csv)
    fieldnames = list(csv_reader.fieldnames or []) + [LOGO_URL_COLUMN]
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    csv_writer.writeheader()

    for district in csv_reader:
        website_url = district.get(WEBSITE_COLUMN, "")
        logo_url = ""
        if website_url:
            logo_url = find_best_logo_url_from_site(website_url)
        district[LOGO_URL_COLUMN] = logo_url
        csv_writer.writerow(district)
        sys.stdout.flush()


@main.command()
@click.argument("input_csv", type=click.File("r", encoding="utf-8"))
@click.argument("previous_csv", type=click.File("r", encoding="utf-8"))
def all_continue(input_csv: t.IO[str], previous_csv: t.IO[str]) -> None:
    # The previous_csv represents a partial run of the `all` command.
    # We read both input_csv and previous_csv in parallel, and emit
    # previous_csv rows until they run out, at which point we continue
    # processing input_csv.
    previous_reader = csv.DictReader(previous_csv)
    previous_rows = list(previous_reader)
    csv_reader = csv.DictReader(input_csv)
    fieldnames = list(csv_reader.fieldnames or []) + [LOGO_URL_COLUMN]
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    csv_writer.writeheader()
    previous_index = 0
    for district in csv_reader:
        if previous_index < len(previous_rows):
            # Emit from previous
            csv_writer.writerow(previous_rows[previous_index])
            previous_index += 1
            sys.stdout.flush()
            continue

        website_url = district.get(WEBSITE_COLUMN, "")
        logo_url = ""
        if website_url:
            logo_url = find_best_logo_url_from_site(website_url)
        district[LOGO_URL_COLUMN] = logo_url
        csv_writer.writerow(district)
        sys.stdout.flush()


@main.command()
@click.argument("website_url")
def one(website_url: str) -> None:
    logo_url = find_best_logo_url_from_site(website_url)
    if logo_url:
        print(logo_url)
    else:
        print("No logo found.")


if __name__ == "__main__":
    main()
