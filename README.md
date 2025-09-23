# cities-db

A database of ~32,000 cities (cities in the world with population > 15,000), compressed into a format suitable for auto-complete on web pages (~283 KB) or mobile apps.

The data is fetched from [GeoNames.org](https://geonames.org), and processed into a custom format.

## Why?

This library was created for [findstarlink.com](https://findstarlink.com). Using the Google Maps API for auto-complete, or hosting a dedicated API endpoint, would be pretty expensive. I don't see why we need a remote service for this.

Bandwidth usage accounts for the majority of FindStarlink's running costs (even after using a CDN). So it was pretty important to keep this library's file size as small as possible.

## What does this do?

Achieves significant compression through:
- Delta encoding for sorted geohashes
- Delta encoding for region/country IDs
- Token-based string compression
- Binary format with minimal overhead

The naive approach would be to store the data as an SQLite database, which results in a compressed file size of 1.4 MB (2.55 MB uncompressed).

This library produces a bundle size of just 283 KB (573 KB uncompressed), by using the methods described above.

This makes it quite useful for transferring over the web - for a fast, fully-local auto-complete dropdown of most of the major cities of the world.

## Why only cities with population > 15k?

This number is sufficient for FindStarlink, as satellite predictions do not change significantly over a few hundred kilometers or miles. Therefore, it is unnecessary to include every place in the world.

However, you can increase the number of cities by downloading a different dataset in [import-db.sh](import-db.sh).

## Features

- **Efficient Binary Format**: Delta-compressed geohashes, region/country IDs, and token-based string storage
- **Fast Lookups**: O(log n) binary search on sorted geohashes  
- **Single File Distribution**: All data bundled into one file for easy web transmission
- **Token-based Compression**: String data compressed using a shared vocabulary
- **Browser and Node.js Compatible**: Works in both environments

## Bundle Format

The bundle file (`cities_bundle.bin`) contains:

1. **Header (32 bytes)**:
   - Magic bytes "CITYDB01" (8 bytes)
   - Vocabulary entries count (4 bytes)
   - Cities count (4 bytes) 
   - Regions count (4 bytes)
   - Countries count (4 bytes)
   - Reserved space (8 bytes)

2. **Vocabulary Section**:
   - Token ID (2 bytes, big-endian)
   - Token length (1 byte)
   - Token text (UTF-8)

3. **Data Sections** (each prefixed with size):
   - Delta-compressed geohashes
   - Delta-compressed region IDs
   - Delta-compressed country IDs
   - Token-compressed city names
   - Token-compressed region names
   - Token-compressed country names

## API Reference

### Class: CityDatabase

#### Constructor
```javascript
const db = new CityDatabase();
```

#### Methods

##### `loadFromBundle(buffer)`
Load database from bundled binary data.
- **buffer**: `ArrayBuffer` - The bundled binary data
- **Returns**: `Promise<void>`

```javascript
const response = await fetch('cities_bundle.bin');
const buffer = await response.arrayBuffer();
await db.loadFromBundle(buffer);
```

##### `getCityFromGeohash(geohash)`
Get formatted city information from geohash.
- **geohash**: `string` - The geohash to look up
- **Returns**: `string|null` - Formatted "cityName, regionName, countryName" or null

```javascript
const result = db.getCityFromGeohash('u14zy');
// Returns: "'s-Gravenzande, Zuid-Holland, Netherlands"
```

##### `findCityByGeohash(geohash)`
Find city object by geohash.
- **geohash**: `string` - The geohash to search for
- **Returns**: `Object|null` - City object with {geohash, name, regionId, countryId}

```javascript
const city = db.findCityByGeohash('u14zy');
// Returns: {geohash: 'u14zy', name: "'s-Gravenzande", regionId: 3146, countryId: 224}
```

##### `findCitiesByGeohashPrefix(prefix, limit)`
Find cities by geohash prefix (useful for proximity searches).
- **prefix**: `string` - The geohash prefix to search for
- **limit**: `number` - Maximum results (default: 50)
- **Returns**: `Array` - Array of city objects

```javascript
const cities = db.findCitiesByGeohashPrefix('u14', 10);
// Returns array of up to 10 cities with geohashes starting with 'u14'
```

##### `getStats()`
Get database statistics.
- **Returns**: `Object` - {cities, regions, countries, vocabularySize}

```javascript
const stats = db.getStats();
// Returns: {cities: 32446, regions: 3864, countries: 252, vocabularySize: 1000}
```

## Usage Examples

### Browser Usage

```html
<!DOCTYPE html>
<html>
<head>
    <script src="cityDatabase.js"></script>
</head>
<body>
    <script>
        async function loadAndTest() {
            const db = new CityDatabase();
            
            // Load the database
            const response = await fetch('cities_bundle.bin');
            const buffer = await response.arrayBuffer();
            await db.loadFromBundle(buffer);
            
            // Look up a city
            const result = db.getCityFromGeohash('u14zy');
            console.log(result); // "'s-Gravenzande, Zuid-Holland, Netherlands"
            
            // Search by prefix
            const nearby = db.findCitiesByGeohashPrefix('u14', 5);
            console.log(nearby);
        }
        
        loadAndTest();
    </script>
</body>
</html>
```

### Node.js Usage

```javascript
const fs = require('fs');
const CityDatabase = require('./cityDatabase.js');

async function example() {
    const db = new CityDatabase();
    
    // Load the database
    const buffer = fs.readFileSync('cities_bundle.bin');
    await db.loadFromBundle(buffer.buffer);
    
    // Look up cities
    console.log(db.getCityFromGeohash('u14zy'));
    console.log(db.getCityFromGeohash('u15y0'));
    
    // Get statistics
    console.log(db.getStats());
}

example();
```
