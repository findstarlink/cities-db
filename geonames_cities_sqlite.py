import sys
import sqlite3
import csv

# Usage: script.py output.db countryInfo.txt cities15000.txt admin1CodesASCII.txt
if len(sys.argv) != 5:
    print(f"usage: {sys.argv[0]} output.db countryInfo.txt cities15000.txt admin1CodesASCII.txt", file=sys.stderr)
    sys.exit(1)

file, in_country, in_cities, in_admin1 = sys.argv[1:]

conn = sqlite3.connect(file)
c = conn.cursor()


def do_sql(sql):
    print(sql, file=sys.stderr)
    c.execute(sql)
    conn.commit()


def do_file(infile, table_name, expected_fields):
    with open(infile, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        sql = f"INSERT INTO {table_name} VALUES ({','.join(['?']*expected_fields)})"
        print(sql, file=sys.stderr)
        batch = []
        for i, row in enumerate(reader):
            if not row or row[0].startswith("#"):
                continue
            if len(row) != expected_fields:
                print(f"{infile}:{i+1}: got {len(row)} fields (expected {expected_fields})", file=sys.stderr)
                continue
            batch.append(row)
            if len(batch) == 1000:
                c.executemany(sql, batch)
                conn.commit()
                batch = []
        if batch:
            c.executemany(sql, batch)
            conn.commit()


do_sql("DROP TABLE IF EXISTS geoname")
do_sql(
    """CREATE TABLE geoname (
    geonameid INTEGER PRIMARY KEY,
    name TEXT,
    asciiname TEXT,
    alternatenames TEXT,
    latitude REAL,
    longitude REAL,
    fclass TEXT,
    fcode TEXT,
    country TEXT,
    cc2 TEXT,
    admin1 TEXT,
    admin2 TEXT,
    admin3 TEXT,
    admin4 TEXT,
    population INTEGER,
    elevation INTEGER,
    gtopo30 INTEGER,
    timezone TEXT,
    moddate TEXT
)"""
)

do_sql("DROP TABLE IF EXISTS admin1")
do_sql(
    """CREATE TABLE admin1 (
    key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    asciiname TEXT NOT NULL,
    geonameid INTEGER NOT NULL
)"""
)

do_sql("DROP TABLE IF EXISTS country")
do_sql(
    """CREATE TABLE country (
    ISO TEXT PRIMARY KEY,
    ISO3 TEXT NOT NULL,
    IsoNumeric TEXT NOT NULL,
    fips TEXT NOT NULL,
    Country TEXT NOT NULL,
    Capital TEXT NOT NULL,
    Area INTEGER NOT NULL,
    Population INTEGER NOT NULL,
    Continent TEXT NOT NULL,
    tld TEXT NOT NULL,
    CurrencyCode TEXT NOT NULL,
    CurrencyName TEXT NOT NULL,
    Phone TEXT NOT NULL,
    PostalCodeFormat TEXT,
    PostalCodeRegex TEXT,
    Languages TEXT NOT NULL,
    geonameid INTEGER NOT NULL,
    neighbours TEXT NOT NULL,
    EquivalentFipsCode TEXT NOT NULL
)"""
)

do_file(in_country, "country", 19)
do_file(in_cities, "geoname", 19)
do_file(in_admin1, "admin1", 4)

do_sql("DROP TABLE IF EXISTS geoname_fulltext")
do_sql(
    """CREATE VIRTUAL TABLE geoname_fulltext USING fts3(
    geonameid INTEGER, longname TEXT,
    asciiname TEXT, admin1 TEXT, country TEXT,
    population INTEGER, latitude REAL, longitude REAL, timezone TEXT
)"""
)

do_sql(
    """INSERT INTO geoname_fulltext
SELECT g.geonameid, g.asciiname || ', ' || a.asciiname || ', ' || c.Country,
       g.asciiname, a.asciiname, c.Country,
       g.population, g.latitude, g.longitude, g.timezone
FROM geoname g, admin1 a, country c
WHERE g.country = c.ISO
  AND g.country || '.' || g.admin1 = a.key
"""
)

conn.commit()
conn.close()
