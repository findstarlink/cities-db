# apt install libdbi-perl
# apt install libdbd-sqlite3-perl

mkdir -p source

curl -o source/countryInfo.txt http://download.geonames.org/export/dump/countryInfo.txt
curl -o source/admin1CodesASCII.txt http://download.geonames.org/export/dump/admin1CodesASCII.txt
curl -o source/cities15000.zip http://download.geonames.org/export/dump/cities15000.zip
unzip source/cities15000.zip -d source/
./geonames_cities_sqlite.pl cities.db \
    source/countryInfo.txt source/cities15000.txt source/admin1CodesASCII.txt

