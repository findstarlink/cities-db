"""
The script compress.py compresses cities data by converting each city's information into a delta-encoded format.

Instead of storing absolute values for each city's ID, latitude, longitude, country, and admin1 code, it
stores the difference (delta) from the previous city's value. If a value doesn't change, it is omitted (empty string).

This reduces redundancy and file size, especially when the data is sorted and values change gradually.
"""

import sys

if len(sys.argv) < 3:
    print("Not enough arguments")
    exit()

source_file = sys.argv[1]
dest_file = sys.argv[2]
do_compress = False if len(sys.argv) > 3 and sys.argv[3] == "false" else True

f = open(source_file, "r")
lines = f.readlines()
f.close()

f = open(dest_file, "w")

prevId = 0
prevLat = 0
prevLng = 0
prevCountry = 0
prevAdmin1 = 0

f.write("var cityInfo = [\n")

parts = []

for line in lines:
    line = line.replace("\n", "")
    p = line.split("|")

    if p[4] == "":
        p[4] = "-1"

    id = int(p[0])
    lat = int(p[1])
    lng = int(p[2])
    country = int(p[3])
    admin1 = int(p[4])

    id_d = id - prevId
    lat_d = lat - prevLat
    lng_d = lng - prevLng
    country_d = country - prevCountry
    admin1_d = admin1 - prevAdmin1

    id_s = str(id_d)
    lat_s = str(lat_d) if lat_d != 0 else ""
    lng_s = str(lng_d) if lng_d != 0 else ""
    country_s = str(country_d) if country_d != 0 else ""
    admin1_s = str(admin1_d) if admin1_d != 0 else ""

    if do_compress:
        l = [id_s, lat_s, lng_s, country_s, admin1_s]
    else:
        l = [str(id), "%.1f" % (lat / 10.0), "%.1f" % (lng / 10.0), str(country), str(admin1)]

    parts.append("[" + ",".join(l) + "]")

    prevId = id
    prevLat = lat
    prevLng = lng
    prevCountry = country
    prevAdmin1 = admin1

f.write(",\n".join(parts))

f.write("\n];")

f.close()
