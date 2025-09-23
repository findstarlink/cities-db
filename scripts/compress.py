#!/usr/bin/env python3
"""
Compress cities_geohash_tokenized_blob.db (BLOB format) into binary format with delta encoding.

This variant handles databases where tokens are stored as BLOBs (2 bytes per token).

Creates six binary output files in intermediates/blobs/:
1. cities_geohash.bin - Delta-encoded geohash with 4-bit prefix for delta length
2. cities_region_id.bin - Delta-encoded region_id as 2-byte integers
3. cities_country_id.bin - Delta-encoded country_id as 2-byte integers
4. cities_name_tokens.bin - Direct binary tokens with 1-byte length prefix
5. regions_name_tokens.bin - Direct binary tokens with 1-byte length prefix
6. countries_name_tokens.bin - Direct binary tokens with 1-byte length prefix

Each file starts with a 4-byte integer indicating the number of rows.
"""

import sqlite3
import argparse
import os
import struct
from typing import List, Tuple, BinaryIO


def calculate_geohash_delta(geohashes: List[str]) -> List[Tuple[int, str]]:
    """
    Calculate delta encoding for geohashes.
    Returns list of (prefix_length, delta_string) tuples.
    """
    if not geohashes:
        return []

    deltas = []
    prev = ""

    for geohash in geohashes:
        # Find common prefix length
        common_len = 0
        min_len = min(len(prev), len(geohash))
        for i in range(min_len):
            if prev[i] == geohash[i]:
                common_len += 1
            else:
                break

        # Delta is the part that's different
        delta = geohash[common_len:]
        deltas.append((common_len, delta))
        prev = geohash

    return deltas


def calculate_integer_deltas(values: List[int]) -> List[int]:
    """
    Calculate delta encoding for integer values.
    Returns list of delta values.
    """
    if not values:
        return []

    deltas = [values[0]]  # First value is stored as-is
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        deltas.append(delta)

    return deltas


def write_geohash_binary(geohashes: List[str], output_path: str):
    """
    Write delta-encoded geohashes to binary file.
    Each row: 4-bit prefix length + delta string
    """
    deltas = calculate_geohash_delta(geohashes)

    with open(output_path, "wb") as f:
        # Write number of rows (4 bytes)
        f.write(struct.pack("<I", len(geohashes)))

        for prefix_len, delta in deltas:
            # Pack prefix length (4 bits) with delta length (4 bits) in first byte
            delta_len = len(delta)
            if prefix_len > 15 or delta_len > 15:
                raise ValueError(f"Prefix or delta length too large: {prefix_len}, {delta_len}")

            header_byte = (prefix_len << 4) | delta_len
            f.write(struct.pack("B", header_byte))

            # Write delta string
            f.write(delta.encode("ascii"))


def write_integer_deltas_binary(values: List[int], output_path: str):
    """
    Write delta-encoded integers to binary file.
    Each value is a signed 2-byte integer.
    """
    deltas = calculate_integer_deltas(values)

    with open(output_path, "wb") as f:
        # Write number of rows (4 bytes)
        f.write(struct.pack("<I", len(values)))

        for delta in deltas:
            # Write as signed 2-byte integer
            if delta < -32768 or delta > 32767:
                raise ValueError(f"Delta value out of range for 2-byte signed int: {delta}")
            f.write(struct.pack("<h", delta))


def write_tokens_binary(token_blobs: List[bytes], output_path: str):
    """
    Write token blobs to binary file.
    Each row: 1-byte length + blob data
    """
    with open(output_path, "wb") as f:
        # Write number of rows (4 bytes)
        f.write(struct.pack("<I", len(token_blobs)))

        for blob in token_blobs:
            # Write length (1 byte)
            blob_len = len(blob)
            if blob_len > 255:
                raise ValueError(f"Token blob too large: {blob_len} bytes")
            f.write(struct.pack("B", blob_len))

            # Write blob data
            f.write(blob)


def read_geohash_binary(input_path: str) -> List[str]:
    """
    Decode delta-encoded geohashes from binary file.
    """
    geohashes = []

    with open(input_path, "rb") as f:
        # Read number of rows
        num_rows = struct.unpack("<I", f.read(4))[0]

        prev_geohash = ""
        for _ in range(num_rows):
            # Read header byte
            header_byte = struct.unpack("B", f.read(1))[0]
            prefix_len = (header_byte >> 4) & 0xF
            delta_len = header_byte & 0xF

            # Read delta string
            delta = f.read(delta_len).decode("ascii")

            # Reconstruct geohash
            geohash = prev_geohash[:prefix_len] + delta
            geohashes.append(geohash)
            prev_geohash = geohash

    return geohashes


def read_integer_deltas_binary(input_path: str) -> List[int]:
    """
    Decode delta-encoded integers from binary file.
    """
    values = []

    with open(input_path, "rb") as f:
        # Read number of rows
        num_rows = struct.unpack("<I", f.read(4))[0]

        prev_value = 0
        for i in range(num_rows):
            # Read delta
            delta = struct.unpack("<h", f.read(2))[0]

            if i == 0:
                # First value is stored as-is
                value = delta
            else:
                # Reconstruct value
                value = prev_value + delta

            values.append(value)
            prev_value = value

    return values


def read_tokens_binary(input_path: str) -> List[bytes]:
    """
    Decode token blobs from binary file.
    """
    token_blobs = []

    with open(input_path, "rb") as f:
        # Read number of rows
        num_rows = struct.unpack("<I", f.read(4))[0]

        for _ in range(num_rows):
            # Read length
            blob_len = struct.unpack("B", f.read(1))[0]

            # Read blob data
            blob = f.read(blob_len)
            token_blobs.append(blob)

    return token_blobs


def compress_database(input_db: str, output_dir: str):
    """
    Compress the cities_tokenized.db into binary files.
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    conn = sqlite3.connect(input_db)
    cursor = conn.cursor()

    # Read cities data, sorted by geohash
    print("Reading cities data...")
    cursor.execute("SELECT geohash, city_name_tokens, region_id, country_id FROM cities ORDER BY geohash")
    cities_data = cursor.fetchall()

    geohashes = [row[0] for row in cities_data]
    city_tokens = [row[1] for row in cities_data]
    region_ids = [row[2] for row in cities_data]
    country_ids = [row[3] for row in cities_data]

    # Read regions data
    print("Reading regions data...")
    cursor.execute("SELECT region_name_tokens FROM regions ORDER BY region_id")
    region_tokens = [row[0] for row in cursor.fetchall()]

    # Read countries data
    print("Reading countries data...")
    cursor.execute("SELECT country_name_tokens FROM countries ORDER BY country_id")
    country_tokens = [row[0] for row in cursor.fetchall()]

    conn.close()

    print(f"Compressing {len(geohashes)} cities, {len(region_tokens)} regions, {len(country_tokens)} countries")

    # Write compressed files
    print("Writing cities_geohash.bin...")
    write_geohash_binary(geohashes, os.path.join(output_dir, "cities_geohash.bin"))

    print("Writing cities_region_id.bin...")
    write_integer_deltas_binary(region_ids, os.path.join(output_dir, "cities_region_id.bin"))

    print("Writing cities_country_id.bin...")
    write_integer_deltas_binary(country_ids, os.path.join(output_dir, "cities_country_id.bin"))

    print("Writing cities_name_tokens.bin...")
    write_tokens_binary(city_tokens, os.path.join(output_dir, "cities_name_tokens.bin"))

    print("Writing regions_name_tokens.bin...")
    write_tokens_binary(region_tokens, os.path.join(output_dir, "regions_name_tokens.bin"))

    print("Writing countries_name_tokens.bin...")
    write_tokens_binary(country_tokens, os.path.join(output_dir, "countries_name_tokens.bin"))

    print("Compression complete!")


def decompress_database(
    input_dir: str,
) -> Tuple[List[str], List[bytes], List[int], List[int], List[bytes], List[bytes]]:
    """
    Decompress binary files back to original arrays.
    Returns: (geohashes, city_tokens, region_ids, country_ids, region_tokens, country_tokens)
    """
    print("Decompressing binary files...")

    geohashes = read_geohash_binary(os.path.join(input_dir, "cities_geohash.bin"))
    region_ids = read_integer_deltas_binary(os.path.join(input_dir, "cities_region_id.bin"))
    country_ids = read_integer_deltas_binary(os.path.join(input_dir, "cities_country_id.bin"))
    city_tokens = read_tokens_binary(os.path.join(input_dir, "cities_name_tokens.bin"))
    region_tokens = read_tokens_binary(os.path.join(input_dir, "regions_name_tokens.bin"))
    country_tokens = read_tokens_binary(os.path.join(input_dir, "countries_name_tokens.bin"))

    print("Decompression complete!")

    return geohashes, city_tokens, region_ids, country_ids, region_tokens, country_tokens


def verify_compression(input_db: str, output_dir: str):
    """
    Verify that compression and decompression work correctly.
    """
    print("Verifying compression...")

    # Read original data
    conn = sqlite3.connect(input_db)
    cursor = conn.cursor()

    cursor.execute("SELECT geohash, city_name_tokens, region_id, country_id FROM cities ORDER BY geohash")
    original_cities = cursor.fetchall()

    cursor.execute("SELECT region_name_tokens FROM regions ORDER BY region_id")
    original_regions = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT country_name_tokens FROM countries ORDER BY country_id")
    original_countries = [row[0] for row in cursor.fetchall()]

    conn.close()

    # Decompress
    geohashes, city_tokens, region_ids, country_ids, region_tokens, country_tokens = decompress_database(output_dir)

    # Verify
    errors = 0

    # Check cities
    for i, (orig_geohash, orig_tokens, orig_region_id, orig_country_id) in enumerate(original_cities):
        if i >= len(geohashes):
            print(f"ERROR: Missing city at index {i}")
            errors += 1
            continue

        if geohashes[i] != orig_geohash:
            print(f"ERROR: Geohash mismatch at {i}: {geohashes[i]} != {orig_geohash}")
            errors += 1

        if city_tokens[i] != orig_tokens:
            print(f"ERROR: City tokens mismatch at {i}")
            errors += 1

        if region_ids[i] != orig_region_id:
            print(f"ERROR: Region ID mismatch at {i}: {region_ids[i]} != {orig_region_id}")
            errors += 1

        if country_ids[i] != orig_country_id:
            print(f"ERROR: Country ID mismatch at {i}: {country_ids[i]} != {orig_country_id}")
            errors += 1

    # Check regions
    for i, orig_tokens in enumerate(original_regions):
        if i >= len(region_tokens):
            print(f"ERROR: Missing region at index {i}")
            errors += 1
            continue

        if region_tokens[i] != orig_tokens:
            print(f"ERROR: Region tokens mismatch at {i}")
            errors += 1

    # Check countries
    for i, orig_tokens in enumerate(original_countries):
        if i >= len(country_tokens):
            print(f"ERROR: Missing country at index {i}")
            errors += 1
            continue

        if country_tokens[i] != orig_tokens:
            print(f"ERROR: Country tokens mismatch at {i}")
            errors += 1

    if errors == 0:
        print("✓ Verification successful! All data matches.")
    else:
        print(f"✗ Verification failed with {errors} errors.")

    return errors == 0


def main():
    parser = argparse.ArgumentParser(
        description="Compress cities_geohash_tokenized.db (BLOB format) into binary format"
    )
    parser.add_argument("input_db", nargs="?", help="Input SQLite database file (cities_geohash_tokenized.db)")
    parser.add_argument("--output-dir", default="intermediates/bin_blob", help="Output directory for binary files")
    parser.add_argument("--verify", action="store_true", help="Verify compression by decompressing and comparing")
    parser.add_argument("--decompress-only", action="store_true", help="Only decompress existing binary files")

    args = parser.parse_args()

    if not args.decompress_only:
        if not args.input_db:
            print("ERROR: input_db is required when not using --decompress-only")
            return 1
        if not os.path.exists(args.input_db):
            print(f"ERROR: Input database {args.input_db} does not exist")
            return 1

        compress_database(args.input_db, args.output_dir)

        if args.verify:
            if not verify_compression(args.input_db, args.output_dir):
                return 1
    else:
        decompress_database(args.output_dir)

    return 0


if __name__ == "__main__":
    exit(main())
