if [ -e build ]; then
	echo "Cleaning up existing build directory..."
	rm -r build
fi

mkdir build

# assumes that ./import-db.sh has already been run

python create_simplified_cities.py cities.db build/cities_simple.db
python create_geohash_cities.py build/cities_simple.db build/cities_geohash.db
