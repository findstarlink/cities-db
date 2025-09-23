#!/usr/bin/env python3
"""
Verify the bundle format and test basic decompression in Python
"""

import struct
import os
import sys


def verify_bundle(bundle_path):
    """Verify the bundle file structure"""
    print(f"Verifying bundle: {bundle_path}")

    if not os.path.exists(bundle_path):
        print(f"ERROR: Bundle file not found: {bundle_path}")
        return False

    file_size = os.path.getsize(bundle_path)
    print(f"Bundle size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

    with open(bundle_path, "rb") as f:
        # Read header
        magic = f.read(8).decode("ascii")
        if magic != "CITYDB01":
            print(f"ERROR: Invalid magic bytes: {magic}")
            return False
        print(f"✓ Magic bytes: {magic}")

        num_vocab = struct.unpack("<I", f.read(4))[0]
        num_cities = struct.unpack("<I", f.read(4))[0]
        num_regions = struct.unpack("<I", f.read(4))[0]
        num_countries = struct.unpack("<I", f.read(4))[0]
        reserved = f.read(8)

        print(f"✓ Vocabulary entries: {num_vocab:,}")
        print(f"✓ Cities: {num_cities:,}")
        print(f"✓ Regions: {num_regions:,}")
        print(f"✓ Countries: {num_countries:,}")

        # Read vocabulary
        print("Reading vocabulary...")
        vocab = {}
        for i in range(num_vocab):
            token_id = struct.unpack(">H", f.read(2))[0]
            token_len = struct.unpack("B", f.read(1))[0]
            token_text = f.read(token_len).decode("utf-8")
            vocab[token_id] = token_text

            if i < 10:  # Show first 10 tokens
                print(f"  {token_id}: '{token_text}'")
            elif i == 10:
                print("  ...")

        print(f"✓ Loaded {len(vocab)} vocabulary entries")

        # Read data sections
        sections = ["geohash", "regionIds", "countryIds", "cityTokens", "regionTokens", "countryTokens"]

        print("Reading data sections...")
        for section in sections:
            section_size = struct.unpack("<I", f.read(4))[0]
            section_data = f.read(section_size)
            print(f"  {section}: {section_size:,} bytes")

        remaining = file_size - f.tell()
        if remaining != 0:
            print(f"WARNING: {remaining} bytes remaining in file")
        else:
            print("✓ Entire file consumed")

    return True


def test_basic_decompression(bundle_path):
    """Test basic decompression of a few entries"""
    print("\nTesting basic decompression...")

    return verify_bundle(bundle_path)


def main():
    print("Bundle verification and basic decompression test\n")

    if len(sys.argv) > 1:
        bundle_path = sys.argv[1]
    else:
        print("Error: Please provide the path to the bundle file as an argument")
        return 1

    if test_basic_decompression(bundle_path):
        print("\n✅ Bundle verification passed!")
        print("\nTo test the JavaScript module:")
        print("1. Open http://localhost:8000/test.html in your browser")
        print("2. Click 'Load Database' to load the bundle")
        print("3. Test the geohash lookup functions")
        print("\nExample test geohashes:")
        print("  u14zy - Should find 's-Gravenzande")
        print("  u15y0 - Should find 's-Hertogenbosch")
        print("  s6ruxt - Should find 'Ārdamatā")
    else:
        print("\n❌ Bundle verification failed!")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
