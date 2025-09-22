#!/usr/bin/env python3
"""
Create a simplified SQLite database from the existing cities.db with normalized tables.

This script creates three tables:
- cities (city_name, latitude, longitude, country_id, region_id)
- countries (country_id, country_name)
- regions (region_id, region_name)

country_id and region_id are auto-incremented row IDs, and the cities table
references these instead of text-based identifiers.

The resulting database is much cleaner and smaller, using integer foreign keys
instead of text-based lookups, which improves both storage efficiency and
query performance.

Input: cities.db (with geoname, country, admin1 tables from GeoNames.org)
Output: A simplified SQLite database with normalized structure

Usage:
    python create_simplified_cities_db.py cities.db simple_cities.db

Example queries on the output database:

    -- Get cities in a specific country
    SELECT c.city_name, c.latitude, c.longitude
    FROM cities c
    JOIN countries co ON c.country_id = co.country_id
    WHERE co.country_name = 'United States';

    -- Get cities in a specific region
    SELECT c.city_name, r.region_name, co.country_name
    FROM cities c
    LEFT JOIN regions r ON c.region_id = r.region_id
    JOIN countries co ON c.country_id = co.country_id
    WHERE r.region_name LIKE '%California%';

    -- Count cities per country
    SELECT co.country_name, COUNT(*) as city_count
    FROM cities c
    JOIN countries co ON c.country_id = co.country_id
    GROUP BY co.country_name
    ORDER BY city_count DESC;
"""

import sqlite3
import sys
import os


def create_simplified_db(input_db_path, output_db_path):
    """
    Create simplified database from the existing cities.db

    Args:
        input_db_path (str): Path to the source cities.db file
        output_db_path (str): Path to the output simplified database
    """
    # Connect to source database
    print(f"Reading from: {input_db_path}")
    source_conn = sqlite3.connect(input_db_path)
    source_cursor = source_conn.cursor()

    # Connect to destination database
    print(f"Creating: {output_db_path}")
    dest_conn = sqlite3.connect(output_db_path)
    dest_cursor = dest_conn.cursor()

    try:
        # Create countries table
        print("Creating countries table...")
        dest_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS countries (
                country_id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_name TEXT NOT NULL
            )
        """
        )

        # Create regions table
        print("Creating regions table...")
        dest_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS regions (
                region_id INTEGER PRIMARY KEY AUTOINCREMENT,
                region_name TEXT NOT NULL
            )
        """
        )

        # Create cities table
        print("Creating cities table...")
        dest_cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cities (
                city_name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                country_id INTEGER NOT NULL,
                region_id INTEGER,
                FOREIGN KEY (country_id) REFERENCES countries (country_id),
                FOREIGN KEY (region_id) REFERENCES regions (region_id)
            )
        """
        )

        # Build countries mapping
        print("Populating countries table...")
        source_cursor.execute("SELECT DISTINCT ISO, Country FROM country ORDER BY Country")
        countries = source_cursor.fetchall()

        country_map = {}  # ISO code -> country_id
        for iso_code, country_name in countries:
            dest_cursor.execute("INSERT INTO countries (country_name) VALUES (?)", (country_name,))
            country_id = dest_cursor.lastrowid
            country_map[iso_code] = country_id

        print(f"Inserted {len(countries)} countries")

        # Build regions mapping
        print("Populating regions table...")
        source_cursor.execute(
            """
            SELECT DISTINCT a.key, a.name
            FROM admin1 a
            ORDER BY a.name
        """
        )
        regions = source_cursor.fetchall()

        region_map = {}  # admin1 key -> region_id
        for admin1_key, region_name in regions:
            dest_cursor.execute("INSERT INTO regions (region_name) VALUES (?)", (region_name,))
            region_id = dest_cursor.lastrowid
            region_map[admin1_key] = region_id

        print(f"Inserted {len(regions)} regions")

        # Populate cities table
        print("Populating cities table...")
        source_cursor.execute(
            """
            SELECT g.name, g.latitude, g.longitude, g.country, g.admin1
            FROM geoname g
            WHERE g.fclass = 'P' AND g.population > 0
            ORDER BY g.population DESC
        """
        )

        cities_inserted = 0
        cities_skipped = 0
        coordinates_seen = set()  # Track coordinates to avoid duplicates
        duplicates_removed = 0

        for city_name, latitude, longitude, country_iso, admin1_code in source_cursor:
            # Create coordinate key for deduplication
            coord_key = (round(latitude, 6), round(longitude, 6))

            # Skip if we've already seen these coordinates
            if coord_key in coordinates_seen:
                duplicates_removed += 1
                continue

            # Create admin1 key (country.admin1)
            admin1_key = f"{country_iso}.{admin1_code}"

            # Look up foreign keys
            country_id = country_map.get(country_iso)
            region_id = region_map.get(admin1_key)

            # Only skip if country_id is missing (required), but allow null region_id
            if country_id:
                dest_cursor.execute(
                    """
                    INSERT INTO cities (city_name, latitude, longitude, country_id, region_id)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (city_name, latitude, longitude, country_id, region_id),
                )
                coordinates_seen.add(coord_key)
                cities_inserted += 1

                # Warn about missing region but don't skip the city
                # if not region_id:
                #     print(f"Warning: Unknown region '{admin1_key}' for city '{city_name}' - setting region_id to null")
            else:
                cities_skipped += 1
                print(f"Warning: Unknown country '{country_iso}' for city '{city_name}' - skipping city")

        print(f"Inserted {cities_inserted} cities")
        if duplicates_removed > 0:
            print(f"Removed {duplicates_removed} duplicate cities with identical coordinates")
        if cities_skipped > 0:
            print(f"Skipped {cities_skipped} cities due to missing country references")

        # Create indexes for better query performance
        print("Creating indexes...")
        dest_cursor.execute("CREATE INDEX idx_cities_country ON cities (country_id)")
        dest_cursor.execute("CREATE INDEX idx_cities_region ON cities (region_id)")
        dest_cursor.execute("CREATE INDEX idx_cities_name ON cities (city_name)")

        # Commit changes
        dest_conn.commit()

        # Print summary statistics
        print("\nDatabase creation complete!")
        print("=" * 50)

        dest_cursor.execute("SELECT COUNT(*) FROM countries")
        country_count = dest_cursor.fetchone()[0]
        print(f"Countries: {country_count}")

        dest_cursor.execute("SELECT COUNT(*) FROM regions")
        region_count = dest_cursor.fetchone()[0]
        print(f"Regions: {region_count}")

        dest_cursor.execute("SELECT COUNT(*) FROM cities")
        city_count = dest_cursor.fetchone()[0]
        print(f"Cities: {city_count}")

        # Show sample data
        print(f"\nSample cities:")
        dest_cursor.execute(
            """
            SELECT c.city_name, c.latitude, c.longitude, co.country_name, r.region_name
            FROM cities c
            JOIN countries co ON c.country_id = co.country_id
            LEFT JOIN regions r ON c.region_id = r.region_id
            LIMIT 5
        """
        )

        for row in dest_cursor.fetchall():
            city, lat, lng, country, region = row
            region_display = region if region else "No region"
            print(f"  {city} ({lat:.4f}, {lng:.4f}) - {region_display}, {country}")

        # Show database size
        if os.path.exists(output_db_path):
            size_bytes = os.path.getsize(output_db_path)
            size_mb = size_bytes / (1024 * 1024)
            print(f"\nDatabase size: {size_mb:.2f} MB ({size_bytes:,} bytes)")

    except Exception as e:
        print(f"Error creating database: {e}")
        dest_conn.rollback()
        raise
    finally:
        source_conn.close()
        dest_conn.close()


def main():
    """Main function to handle command line arguments and run the script"""
    if len(sys.argv) != 3:
        print("Usage: python create_simplified_cities_db.py <input_cities.db> <output_simple.db>")
        print()
        print("Example:")
        print("  python create_simplified_cities_db.py cities.db simple_cities.db")
        sys.exit(1)

    input_db = sys.argv[1]
    output_db = sys.argv[2]

    # Validate input file exists
    if not os.path.exists(input_db):
        print(f"Error: Input database '{input_db}' not found")
        sys.exit(1)

    # Warn if output file exists
    if os.path.exists(output_db):
        response = input(f"Output file '{output_db}' already exists. Overwrite? (y/N): ")
        if response.lower() not in ["y", "yes"]:
            print("Aborted.")
            sys.exit(0)
        os.remove(output_db)

    try:
        create_simplified_db(input_db, output_db)
        print(f"\nSuccess! Simplified database created at: {output_db}")
    except Exception as e:
        print(f"\nFailed to create database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
