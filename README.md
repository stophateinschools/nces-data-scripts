# Random tools for working with nces data

### Get set up

1. Clone this repo.
2. Install Astral's UV on your dev machine from https://docs.astral.sh/uv/

### Get public school data in CSV format

The process for getting and cleaning public school data from nces.ed.gov is a bit of a pain.

Here's how:

1. Go to their public school search: https://nces.ed.gov/ccd/schoolsearch/
2. Choose a state (but no other filters) and click "Search".
3. Wait. (Sigh.)
4. Scroll down to the bottom of the page and click "Download Excel File".
5. An tiny popup appears. Wait again. (Sigh.)
6. Once the data is ready, you'll see a link in that popup that _also_ says "Download Excel File". Click it.
7. The file has an `.xls` extension but if you take a look at it in a text editor, you'll see it's actually an HTML file. With a bunch of HTML `<table>` tags. (Sigh.)
8. Run `uv run nceshtml2csv.py path/to/schools.xls` to convert the HTML to CSV. The CSV will be written to standard output, you can redirect it with `uv run nceshtml2csv.py path/to/schools.xls > schools.csv`.

Congrats, you now have a CSV file with public school data. 🎉

### Get public school _district_ data in CSV format

You can also download public school _district_ data from the NCES.

Visit https://nces.ed.gov/ccd/districtsearch/ and follow the same steps as above. The same tools will work for converting the `.xls` file to CSV.

We have raw downloads of district data for the following states in the `data/downloads/` folder:

California
District of Columbia
Florida
Georgia
Illinois
Indiana
Maryland
Massachusetts
Michigan
New Jersey
New York
North Carolina
Oregon
Pennsylvania
Virginia
Washington

If you need this data (since we do not commit large files to the repo), ask Dave.

### Get private school data in CSV format

You can download private school data here: https://nces.ed.gov/surveys/pss/privateschoolsearch/

As of this writing, the `nceshtml2csv.py` does not fully support the slightly different HTML that private school search generates. TODO we will need to update this.

### Geocoding schools

It's useful to have exact latitude/longitude coordinates for schools. You can use the `geocode.py` script to do this.

It takes an arbitrary `.csv` file that has the columns `"Street Address"`, `"City"`, `"State"`, and `"ZIP"` and adds two columns, `"Latitude"` and `"Longitude"`.

The script uses the Google Maps Geocoding API, so you'll need to get an API key from Google. (Ask Josh for one.)

Run the script as:

```bash
> uv run geocode.py --api-key ABC123 path/to/schools.csv > path/to/geocoded-schools.csv
```

### Generate data suitable for importing into AirTable

Presumably SHIS' use of AirTable is only temporary, but if you need to convert from `schools.csv` to a `.csv` file that directly matches Josh's current AirTable schema, you can use the `csv2schools.py` script:

```bash
> uv run csv2schools.py path/to/geocoded-schools.csv > path/to/airtable-schools.csv
```

A similar script exists for districts:

```bash
> uv run csv2districts.py path/to/districts.csv > path/to/airtable-districts.csv
```

### Random notes on the data

NCES data contains a unique identifier for both a school _and_ a district. These should really be primary keys in our eventual SQL database.
