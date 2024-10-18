import csv
import httpx
import click
import sys

# Google Geocoding API URL
GOOGLE_MAPS_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json'

@click.command()
@click.argument('input_csv', type=click.File('r'))
@click.option('--api_key', prompt='Google Maps API Key', help='Your Google Maps Geocoding API key.')
@click.option('--start', default=0, type=int, help='Index of the first zero-indexed row to process.')
def geocode_csv(input_csv, api_key, start):
    """
    Geocode addresses in a CSV file using Google Maps Geocoding API and output the result to stdout.
    """
    csv_reader = csv.DictReader(input_csv)
    fieldnames = csv_reader.fieldnames + ['Latitude', 'Longitude']
    csv_writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

    # Skip rows up to the start index
    for _ in range(start):
        next(csv_reader)

    # Write the header to stdout only if start is 0
    if start == 0:
        csv_writer.writeheader()

    # Process each row in the CSV synchronously
    for row in csv_reader:
        # Construct the address (adjust based on your column names)
        address = f"{row['Street Address']}, {row['City']}, {row['State']}, {row['ZIP']}"
        lat, lng = geocode_address(address, api_key)
        row['Latitude'] = lat
        row['Longitude'] = lng
        csv_writer.writerow(row)
        sys.stdout.flush()

def geocode_address(address, api_key):
    """
    Geocode an address using Google Maps Geocoding API with httpx.
    """
    params = {
        'address': address,
        'key': api_key
    }
    response = httpx.get(GOOGLE_MAPS_API_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            geometry = data['results'][0]['geometry']
            lat = geometry['location']['lat']
            lng = geometry['location']['lng']
            return lat, lng
    return None, None  # Return None if geocoding fails

if __name__ == '__main__':
    geocode_csv()
