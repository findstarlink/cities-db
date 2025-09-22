#!/usr/bin/env python3
"""
Create a normalized cities database with geohash-based unique IDs.

This script reads the existing cities_simple.db file and creates a new SQLite database with normalized tables:
- countries: country_id (PK), country_name
- regions: region_id (PK), region_name
- cities: geohash (PK), city_name, region_id (FK), country_id (FK)

The geohash algorithm finds the shortest possible geohash for each city that
doesn't conflict with any other city in the database.
"""

import sqlite3
import geohash
import sys
import os
from collections import defaultdict


def find_optimal_geohashes(cities_data, verbose=True):
    """
    Find the shortest unique geohash for each city.

    Args:
        cities_data: List of tuples (city_id, lat, lng, name)
        verbose: Print progress information

    Returns:
        dict: {city_id: (geohash, precision_used)}
    """
    if verbose:
        print(f"Finding optimal geohashes for {len(cities_data)} cities...")

    # Start with all cities needing processing
    pending_cities = {city[0]: {"lat": city[1], "lng": city[2], "name": city[3]} for city in cities_data}
    final_geohashes = {}

    precision = 1
    max_precision = 12  # Reasonable limit

    while pending_cities and precision <= max_precision:
        if verbose:
            print(f"  Trying precision {precision} for {len(pending_cities)} cities...")

        # Generate geohashes at current precision
        hash_to_cities = defaultdict(list)

        for city_id, city_data in pending_cities.items():
            try:
                ghash = geohash.encode(city_data["lat"], city_data["lng"], precision=precision)
                hash_to_cities[ghash].append(city_id)
            except Exception as e:
                if verbose:
                    print(f"    Error encoding {city_data['name']}: {e}")
                # Use maximum precision for problem coordinates
                ghash = geohash.encode(city_data["lat"], city_data["lng"], precision=max_precision)
                final_geohashes[city_id] = (ghash, max_precision)

        # Find unique geohashes and conflicts
        unique_cities = []
        conflicted_cities = set()

        for ghash, city_list in hash_to_cities.items():
            if len(city_list) == 1:
                # This geohash is unique
                city_id = city_list[0]
                final_geohashes[city_id] = (ghash, precision)
                unique_cities.append(city_id)
            else:
                # Multiple cities have this geohash - need higher precision
                conflicted_cities.update(city_list)

        if verbose and precision <= 8:  # Don't spam for high precisions
            print(f"    Found {len(unique_cities)} unique geohashes, {len(conflicted_cities)} conflicts")

        # Remove successfully processed cities
        for city_id in unique_cities:
            if city_id in pending_cities:
                del pending_cities[city_id]

        precision += 1

    # Handle any remaining conflicts with maximum precision
    for city_id in pending_cities:
        city_data = pending_cities[city_id]
        try:
            ghash = geohash.encode(city_data["lat"], city_data["lng"], precision=max_precision)
            final_geohashes[city_id] = (ghash + f"_{city_id}", max_precision)  # Add ID to ensure uniqueness
            if verbose:
                print(f"    Warning: City {city_data['name']} forced to max precision with ID suffix")
        except Exception as e:
            if verbose:
                print(f"    Error: Cannot process {city_data['name']}: {e}")
            # Use city ID as fallback
            final_geohashes[city_id] = (f"city_{city_id}", 0)

    return final_geohashes


def create_geohash_cities_db(input_db_path, output_db_path):
    """
    Create the new geohash-based cities database with normalized structure.

    Args:
        input_db_path: Path to the existing cities.db file
        output_db_path: Path for the new geohash cities database
    """
    print(f"Reading cities data from: {input_db_path}")
    print(f"Creating new database at: {output_db_path}")

    # Connect to input database
    if not os.path.exists(input_db_path):
        raise FileNotFoundError(f"Input database not found: {input_db_path}")

    input_conn = sqlite3.connect(input_db_path)
    input_cursor = input_conn.cursor()

    # Get all countries
    print("Extracting countries...")
    input_cursor.execute(
        """
    SELECT country_id, country_name
    FROM countries
    ORDER BY country_name
    """
    )
    countries_data = input_cursor.fetchall()

    # Get all regions
    print("Extracting regions...")
    input_cursor.execute(
        """
    SELECT region_id, region_name
    FROM regions
    ORDER BY region_name
    """
    )
    regions_data = input_cursor.fetchall()

    # Get all cities with their location and reference information
    print("Querying cities data...")
    input_cursor.execute(
        """
    SELECT c.city_name, c.latitude, c.longitude, c.country_id, c.region_id,
           co.country_name, r.region_name
    FROM cities c 
    JOIN countries co ON c.country_id = co.country_id
    JOIN regions r ON c.region_id = r.region_id
    WHERE c.latitude IS NOT NULL 
      AND c.longitude IS NOT NULL
      AND c.city_name IS NOT NULL
    ORDER BY c.city_name
    """
    )

    cities_raw_data = input_cursor.fetchall()
    input_conn.close()

    print(f"Found {len(cities_raw_data)} cities with complete data")
    print(f"Found {len(countries_data)} countries")
    print(f"Found {len(regions_data)} regions")

    # Prepare data for geohash generation (row_index, lat, lng, city_name)
    # We'll use row index as a unique identifier since we don't have geonameid
    cities_data = [(i, row[1], row[2], row[0]) for i, row in enumerate(cities_raw_data)]

    # Find optimal geohashes
    geohash_results = find_optimal_geohashes(cities_data)

    # Create output database
    if os.path.exists(output_db_path):
        os.remove(output_db_path)

    output_conn = sqlite3.connect(output_db_path)
    output_cursor = output_conn.cursor()

    # Create the normalized table structure
    print("Creating normalized database schema...")

    # Countries table
    output_cursor.execute(
        """
    CREATE TABLE countries (
        country_id INTEGER PRIMARY KEY,
        country_name TEXT NOT NULL
    )
    """
    )

    # Regions table
    output_cursor.execute(
        """
    CREATE TABLE regions (
        region_id INTEGER PRIMARY KEY,
        region_name TEXT NOT NULL
    )
    """
    )

    # Cities table with foreign keys
    output_cursor.execute(
        """
    CREATE TABLE cities (
        geohash TEXT PRIMARY KEY,
        city_name TEXT NOT NULL,
        region_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        FOREIGN KEY (country_id) REFERENCES countries(country_id),
        FOREIGN KEY (region_id) REFERENCES regions(region_id)
    )
    """
    )

    # Insert countries data
    print("Inserting countries data...")
    output_cursor.executemany("INSERT INTO countries (country_id, country_name) VALUES (?, ?)", countries_data)

    # Insert regions data
    print("Inserting regions data...")
    output_cursor.executemany("INSERT INTO regions (region_id, region_name) VALUES (?, ?)", regions_data)

    # Insert cities data
    print("Inserting cities data...")
    insert_data = []
    precision_stats = defaultdict(int)

    for i, row in enumerate(cities_raw_data):
        city_name, lat, lng, country_id, region_id, country_name, region_name = row
        if i in geohash_results:
            ghash, precision = geohash_results[i]
            insert_data.append((ghash, city_name, region_id, country_id))
            precision_stats[precision] += 1
        else:
            print(f"Warning: No geohash found for city {city_name}")

    output_cursor.executemany(
        "INSERT INTO cities (geohash, city_name, region_id, country_id) VALUES (?, ?, ?, ?)", insert_data
    )

    # Create indexes for faster lookups
    print("Creating indexes...")
    output_cursor.execute("CREATE INDEX idx_cities_city_name ON cities(city_name)")
    output_cursor.execute("CREATE INDEX idx_cities_country ON cities(country_id)")
    output_cursor.execute("CREATE INDEX idx_cities_region ON cities(region_id)")

    output_conn.commit()
    output_conn.close()

    print(f"\nNormalized database created successfully!")
    print(f"Total cities: {len(insert_data)}")
    print(f"Total countries: {len(countries_data)}")
    print(f"Total regions: {len(regions_data)}")
    print("\nGeohash precision distribution:")
    for precision in sorted(precision_stats.keys()):
        count = precision_stats[precision]
        print(f"  Precision {precision:2d}: {count:5d} cities")

    # Verify uniqueness and relationships
    verify_conn = sqlite3.connect(output_db_path)
    verify_cursor = verify_conn.cursor()

    verify_cursor.execute("SELECT COUNT(*), COUNT(DISTINCT geohash) FROM cities")
    total, unique = verify_cursor.fetchone()

    verify_cursor.execute("SELECT COUNT(*) FROM countries")
    country_count = verify_cursor.fetchone()[0]

    verify_cursor.execute("SELECT COUNT(*) FROM regions")
    region_count = verify_cursor.fetchone()[0]

    verify_conn.close()

    print(f"\nVerification:")
    print(f"  Total cities: {total}")
    print(f"  Unique geohashes: {unique}")
    print(f"  All geohashes unique: {'✓' if total == unique else '✗'}")
    print(f"  Countries in database: {country_count}")
    print(f"  Regions in database: {region_count}")


def main():
    """Main function to run the script."""
    if len(sys.argv) not in [1, 3]:
        print(f"Usage: {sys.argv[0]} [input_db] [output_db]")
        print(f"   or: {sys.argv[0]}  (uses default paths)")
        sys.exit(1)

    # Default paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_input = os.path.join(script_dir, "cities_simple.db")
    default_output = os.path.join(script_dir, "cities_geohash.db")

    if len(sys.argv) == 3:
        input_db_path = sys.argv[1]
        output_db_path = sys.argv[2]
    else:
        input_db_path = default_input
        output_db_path = default_output

    try:
        create_geohash_cities_db(input_db_path, output_db_path)
        print(f"\n✓ Success! Created {output_db_path}")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
