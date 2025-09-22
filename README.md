# cities-db

A database of ~32,000 cities (cities in the world with population > 15,000), compressed into a format suitable for auto-complete on web pages (<400 KB) or mobile apps.

The data is fetched from [GeoNames.org](https://geonames.org), and processed into a custom format.

## Why?

This library was created for [findstarlink.com](https://findstarlink.com). Using the Google Maps API for auto-complete, or hosting a dedicated API endpoint, would be pretty expensive. I don't see why we need a remote service for this.

Bandwidth usage accounts for the majority of FindStarlink's running costs (even after using a CDN). So it was pretty important to keep this library's file size as small as possible.

## What does this do?

This project packs the city database by storing only the deltas of the coordinates, country id and division ids. And it doesn't store anything if there is no difference.

The naive approach would be to store the data as an SQLite database, which results in a compressed file size of 759 KB (1.35 MB uncompressed).

This library produces a bundle size of just 389 KB (1.11 MB uncompressed). By reducing the amount of data stored and using text, this format compresses really well, even with simple ZIP compression.

For a fast, fully-local auto-complete dropdown of most of the major cities of the world, a download size of 389 KB is quite acceptable IMO.

## Why only cities with population > 15k?

This number is sufficient for FindStarlink, as satellite predictions do not change significantly over a few hundred kilometers or miles. Therefore, it is unnecessary to include every place in the world.

However, you can increase the number of cities by downloading a different dataset in [import-db.sh](import-db.sh).

## Deployment Targets and Output Data Formats

### Web Deployment Target
**Output Location:** `build/cities_web.js` and `build/cities_web.zip`

**Data Format:**
- **Combined JavaScript file** containing:
  - `countries[]` - Array of country names as strings
  - `admin1[]` - Array of administrative division names as strings
  - `cities[]` - Array of city entries: `[cityName, logPopulation]`
  - `cityInfo[]` - Delta-compressed coordinate and reference data
- **Compression:** ZIP compressed for web delivery (~389 KB compressed, 1.11 MB uncompressed)
- **Usage:** Direct JavaScript inclusion for web autocomplete functionality

### iOS Deployment Target
**Output Location:** `build/` directory with separate TypeScript files

**Data Format:**
- **countries_ios.ts** - TypeScript module with countries array + export statement
- **admin1_ios.ts** - TypeScript module with admin1 divisions array + export statement
- **cities_ios.ts** - TypeScript module with cities array: `[cityName, rowId]` + export statement
- **info_ios.ts** - TypeScript module with uncompressed coordinate data: `[id, lat, lng, countryId, admin1Id]` + export statement
- **Key difference:** Uses uncompressed absolute coordinates (not delta-compressed) and row IDs instead of log population

### Android Deployment Target
**Output Location:** `build/android/` directory structure

**Data Format:**
- **Paginated Java classes** (1000 cities per page):
  - `CitiesDB.java` - Main class with metadata and page references
  - `raw/Cities{N}.java` - City names and offsets arrays for each page
  - `raw/Info{N}.java` - Coordinate and reference data arrays for each page
  - `raw/Countries.java` - Countries array
  - `raw/Admin1.java` - Administrative divisions array
- **Pagination:** Splits data into chunks to work around Java's class member limits
- **Data Types:** Uses Java String[] and int[] arrays

## Data Processing Pipeline

1. **Source Data** (GeoNames.org):
   - Tab-separated text files (countryInfo.txt, cities15000.txt, admin1CodesASCII.txt)
   - Contains ~32,000 cities (with population > 15,000)

2. **Output Generation**:
   - **Web**: Delta compression via `compress.py` for minimal file size
   - **iOS**: TypeScript modules with absolute coordinates
   - **Android**: Paginated Java classes to work around Java's class member limits

## Key Optimizations by Target

- **Web**: Aggressive compression (delta encoding) prioritizing download size
- **iOS**: TypeScript compatibility with absolute coordinates for easier processing
- **Android**: Fast startup since the DB is compiled along with the rest of the code
