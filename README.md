# cities-db

A database of the 15,000 most populated cities, compressed into a format suitable for auto-complete on web pages (<400 KB) or mobile apps.

The data is fetched from [GeoNames.org](https://geonames.org), and processed into a custom format.

## Why?

This library was created for [findstarlink.com](https://findstarlink.com). Using the Google Maps API for auto-complete, or hosting a dedicated API endpoint, would be pretty expensive. I don't see why we need a remote service for this.

Bandwidth usage accounts for the majority of FindStarlink's running costs (even after using a CDN). So it was pretty important to keep this library's file size as small as possible.

## What does this do?

This project packs the city database by storing only the deltas of the coordinates, country id and division ids. And it doesn't store anything if there is no difference.

The naive approach would be to store the data as an SQLite database, which results in a compressed file size of 759 KB (1.35 MB uncompressed).

This library produces a bundle size of just 389 KB (1.11 MB uncompressed). By reducing the amount of data stored and using text, this format compresses really well, even with simple ZIP compression.

For a fast auto-complete dropdown of the 15,000 most populated cities, a download size of 389 KB is quite acceptable IMO.

## Why 15,000 cities?

This number is sufficient for FindStarlink, as satellite predictions do not change significantly over a few hundred kilometers or miles. Therefore, it is unnecessary to include every city in the world.

However, you can increase the number of cities by downloading a different dataset in [import-db.sh](import-db.sh).
