if [ -e build ]; then
	echo "Cleaning up existing build directory..."
	rm -r build
fi

mkdir build

# assumes that ./import-db.sh has already been run

# for non-web targets
python scripts/create_simplified_cities_db.py intermediates/cities.db build/cities_simple.db
python scripts/create_geohash_cities.py build/cities_simple.db build/cities_geohash.db

# for web targets
python scripts/tokenize_names.py build/cities_geohash.db intermediates/cities_geohash_tokenized.db
python scripts/compress.py intermediates/cities_geohash_tokenized.db --output-dir intermediates/bundle_bin --verify
python scripts/bundle.py --bin-dir intermediates/bundle_bin --db intermediates/cities_geohash_tokenized.db --output build/cities_bundle.bin
