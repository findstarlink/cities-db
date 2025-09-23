#!/usr/bin/env python3
"""
Bundle all binary city files and vocabulary into a single web-transmissible file.

Creates a single binary file with the following structure:
1. Header (32 bytes):
   - Magic bytes "CITYDB01" (8 bytes)
   - Number of vocabulary entries (4 bytes, little-endian)
   - Number of cities (4 bytes, little-endian)
   - Number of regions (4 bytes, little-endian)
   - Number of countries (4 bytes, little-endian)
   - Reserved (8 bytes)

2. Vocabulary section:
   - For each vocabulary entry:
     - Token ID (2 bytes, big-endian)
     - Token length (1 byte)
     - Token text (UTF-8 encoded)

3. Data sections (in order):
   - Cities geohash data
   - Cities region IDs
   - Cities country IDs
   - Cities name tokens
   - Regions name tokens
   - Countries name tokens

Each data section is prefixed with its size in bytes (4 bytes, little-endian).
"""

import sqlite3
import struct
import os
import argparse


def extract_vocabulary(db_path: str) -> dict:
    """Extract vocabulary from database as {token_id: token_text}"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT token_id, token FROM vocabulary ORDER BY token_id")
    vocab = {token_id: token for token_id, token in cursor.fetchall()}

    conn.close()
    return vocab


def bundle_files(vocab: dict, bin_dir: str, output_path: str):
    """Bundle all files into a single binary file"""

    # File paths
    files = [
        "cities_geohash.bin",
        "cities_region_id.bin",
        "cities_country_id.bin",
        "cities_name_tokens.bin",
        "regions_name_tokens.bin",
        "countries_name_tokens.bin",
    ]

    # Read all binary files
    file_data = {}
    for filename in files:
        filepath = os.path.join(bin_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Binary file not found: {filepath}")

        with open(filepath, "rb") as f:
            file_data[filename] = f.read()

    # Extract counts from the binary files (first 4 bytes of each)
    num_cities = struct.unpack("<I", file_data["cities_geohash.bin"][:4])[0]
    num_regions = struct.unpack("<I", file_data["regions_name_tokens.bin"][:4])[0]
    num_countries = struct.unpack("<I", file_data["countries_name_tokens.bin"][:4])[0]

    print(f"Bundling {num_cities} cities, {num_regions} regions, {num_countries} countries")
    print(f"Vocabulary size: {len(vocab)} tokens")

    with open(output_path, "wb") as f:
        # Write header
        f.write(b"CITYDB01")  # Magic bytes
        f.write(struct.pack("<I", len(vocab)))  # Number of vocabulary entries
        f.write(struct.pack("<I", num_cities))  # Number of cities
        f.write(struct.pack("<I", num_regions))  # Number of regions
        f.write(struct.pack("<I", num_countries))  # Number of countries
        f.write(b"\x00" * 8)  # Reserved space

        # Write vocabulary section
        for token_id in sorted(vocab.keys()):
            token_text = vocab[token_id]
            token_bytes = token_text.encode("utf-8")

            f.write(struct.pack(">H", token_id))  # Token ID (big-endian)
            f.write(struct.pack("B", len(token_bytes)))  # Token length
            f.write(token_bytes)  # Token text

        # Write data sections with size prefixes
        for filename in files:
            data = file_data[filename]
            f.write(struct.pack("<I", len(data)))  # Section size
            f.write(data)  # Section data

    # Report file sizes
    bundle_size = os.path.getsize(output_path)
    print(f"Bundle created: {output_path}")
    print(f"Bundle size: {bundle_size:,} bytes ({bundle_size / 1024 / 1024:.2f} MB)")

    # Calculate compression potential
    total_original = sum(len(data) for data in file_data.values())
    vocab_size = sum(len(token.encode("utf-8")) + 3 for token in vocab.values())  # +3 for ID and length
    total_with_vocab = total_original + vocab_size + 32  # +32 for header

    print(f"Original files total: {total_original:,} bytes")
    print(f"With vocab and header: {total_with_vocab:,} bytes")
    print(f"Bundle overhead: {bundle_size - total_with_vocab:,} bytes")


def main():
    parser = argparse.ArgumentParser(description="Bundle city database files for web transmission")
    parser.add_argument(
        "--db", default="intermediates/cities_geohash_tokenized_blob.db", help="Database file with vocabulary"
    )
    parser.add_argument("--bin-dir", default="intermediates/bin_blob", help="Directory containing binary files")
    parser.add_argument("--output", default="build/cities_bundle.bin", help="Output bundle file")

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.db):
        print(f"ERROR: Database file not found: {args.db}")
        return 1

    if not os.path.exists(args.bin_dir):
        print(f"ERROR: Binary directory not found: {args.bin_dir}")
        return 1

    # Create output directory
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Extract vocabulary
    print("Extracting vocabulary...")
    vocab = extract_vocabulary(args.db)

    # Bundle files
    print("Bundling files...")
    bundle_files(vocab, args.bin_dir, args.output)

    print("Bundle creation complete!")
    return 0


if __name__ == "__main__":
    exit(main())
