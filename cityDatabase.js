/*
 * Copyright (c) 2024 cmdr2
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

/**
 * Efficient JavaScript decompression module for reading compressed city database.
 * 
 * This module can read the binary format created by compress.py and bundle.py,
 * providing fast geohash-based city lookups.
 * 
 * The bundle format contains:
 * 1. Header with magic bytes and counts
 * 2. Vocabulary for token decoding
 * 3. Delta-compressed binary data sections
 * 
 * Features:
 * - Binary search on sorted geohashes for O(log n) lookup
 * - Delta decompression for space efficiency
 * - Token-based string reconstruction
 * - Single bundled file for easy web distribution
 */

class CityDatabase {
    constructor() {
        this.isLoaded = false;
        this.vocabulary = new Map();
        this.cities = [];
        this.regions = [];
        this.countries = [];
        this.geohashIndex = [];
    }

    /**
     * Load the database from a bundled binary file
     * @param {ArrayBuffer} buffer - The bundled binary data
     */
    async loadFromBundle(buffer) {
        const view = new DataView(buffer);
        let offset = 0;

        // Read header
        const magic = new TextDecoder().decode(new Uint8Array(buffer, offset, 8));
        offset += 8;

        if (magic !== 'CITYDB01') {
            throw new Error(`Invalid magic bytes: ${magic}`);
        }

        const numVocab = view.getUint32(offset, true); // little-endian
        offset += 4;
        const numCities = view.getUint32(offset, true);
        offset += 4;
        const numRegions = view.getUint32(offset, true);
        offset += 4;
        const numCountries = view.getUint32(offset, true);
        offset += 4;
        offset += 8; // Skip reserved bytes

        console.log(`Loading database: ${numCities} cities, ${numRegions} regions, ${numCountries} countries, ${numVocab} vocabulary entries`);

        // Read vocabulary
        for (let i = 0; i < numVocab; i++) {
            const tokenId = view.getUint16(offset, false); // big-endian
            offset += 2;
            const tokenLength = view.getUint8(offset);
            offset += 1;
            const tokenBytes = new Uint8Array(buffer, offset, tokenLength);
            const tokenText = new TextDecoder().decode(tokenBytes);
            offset += tokenLength;

            this.vocabulary.set(tokenId, tokenText);
        }

        // Read data sections
        const sections = [
            'geohash',
            'regionIds',
            'countryIds',
            'cityTokens',
            'regionTokens',
            'countryTokens'
        ];

        const sectionData = {};
        for (const section of sections) {
            const sectionSize = view.getUint32(offset, true);
            offset += 4;
            sectionData[section] = new Uint8Array(buffer, offset, sectionSize);
            offset += sectionSize;
        }

        // Decompress each section
        this.cities = this._decompressCitiesData(sectionData, numCities);
        this.regions = this._decompressTokenArray(sectionData.regionTokens);
        this.countries = this._decompressTokenArray(sectionData.countryTokens);

        // Build geohash index for binary search
        this._buildGeohashIndex();

        this.isLoaded = true;
        console.log('Database loaded successfully');
    }

    /**
     * Decompress cities data from all city-related sections
     */
    _decompressCitiesData(sectionData, numCities) {
        const geohashes = this._decompressGeohashes(sectionData.geohash);
        const regionIds = this._decompressIntegerDeltas(sectionData.regionIds);
        const countryIds = this._decompressIntegerDeltas(sectionData.countryIds);
        const cityTokens = this._decompressTokenArray(sectionData.cityTokens);

        const cities = [];
        for (let i = 0; i < numCities; i++) {
            cities.push({
                geohash: geohashes[i],
                name: this._decodeTokens(cityTokens[i]),
                regionId: regionIds[i],
                countryId: countryIds[i]
            });
        }

        return cities;
    }

    /**
     * Decompress delta-encoded geohashes
     */
    _decompressGeohashes(data) {
        const view = new DataView(data.buffer, data.byteOffset);
        const numRows = view.getUint32(0, true);
        const geohashes = [];
        let offset = 4;
        let prevGeohash = '';

        for (let i = 0; i < numRows; i++) {
            const headerByte = view.getUint8(offset);
            offset += 1;

            const prefixLen = (headerByte >> 4) & 0xF;
            const deltaLen = headerByte & 0xF;

            const deltaBytes = new Uint8Array(data.buffer, data.byteOffset + offset, deltaLen);
            const delta = new TextDecoder().decode(deltaBytes);
            offset += deltaLen;

            const geohash = prevGeohash.substring(0, prefixLen) + delta;
            geohashes.push(geohash);
            prevGeohash = geohash;
        }

        return geohashes;
    }

    /**
     * Decompress delta-encoded integers
     */
    _decompressIntegerDeltas(data) {
        const view = new DataView(data.buffer, data.byteOffset);
        const numRows = view.getUint32(0, true);
        const values = [];
        let offset = 4;
        let prevValue = 0;

        for (let i = 0; i < numRows; i++) {
            const delta = view.getInt16(offset, true); // signed little-endian
            offset += 2;

            const value = (i === 0) ? delta : prevValue + delta;
            values.push(value);
            prevValue = value;
        }

        return values;
    }

    /**
     * Decompress token arrays
     */
    _decompressTokenArray(data) {
        const view = new DataView(data.buffer, data.byteOffset);
        const numRows = view.getUint32(0, true);
        const tokenArrays = [];
        let offset = 4;

        for (let i = 0; i < numRows; i++) {
            const blobLen = view.getUint8(offset);
            offset += 1;

            const tokens = [];
            for (let j = 0; j < blobLen; j += 2) {
                if (j + 1 < blobLen) {
                    const tokenId = view.getUint16(offset + j, false); // big-endian
                    tokens.push(tokenId);
                }
            }

            tokenArrays.push(tokens);
            offset += blobLen;
        }

        return tokenArrays;
    }

    /**
     * Decode token IDs to text using vocabulary
     */
    _decodeTokens(tokenIds) {
        return tokenIds.map(id => this.vocabulary.get(id) || `<UNK:${id}>`).join('');
    }

    /**
     * Build index for binary search on geohashes
     */
    _buildGeohashIndex() {
        this.geohashIndex = this.cities.map((city, index) => ({
            geohash: city.geohash,
            index: index
        }));

        // Geohashes should already be sorted, but verify
        for (let i = 1; i < this.geohashIndex.length; i++) {
            if (this.geohashIndex[i].geohash < this.geohashIndex[i - 1].geohash) {
                throw new Error('Geohashes are not sorted - binary search will not work');
            }
        }
    }

    /**
     * Find city by geohash using binary search
     * @param {string} geohash - The geohash to search for
     * @returns {Object|null} - City object or null if not found
     */
    findCityByGeohash(geohash) {
        if (!this.isLoaded) {
            throw new Error('Database not loaded');
        }

        let left = 0;
        let right = this.geohashIndex.length - 1;

        while (left <= right) {
            const mid = Math.floor((left + right) / 2);
            const midGeohash = this.geohashIndex[mid].geohash;

            if (midGeohash === geohash) {
                const cityIndex = this.geohashIndex[mid].index;
                return this.cities[cityIndex];
            } else if (midGeohash < geohash) {
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }

        return null;
    }

    /**
     * Get formatted city information from geohash
     * @param {string} geohash - The geohash to look up
     * @returns {string|null} - Formatted string "cityName, regionName (if not null), countryName" or null
     */
    getCityFromGeohash(geohash) {
        const city = this.findCityByGeohash(geohash);
        if (!city) {
            return null;
        }

        const cityName = city.name;
        const regionName = city.regionId > 0 ? this._decodeTokens(this.regions[city.regionId - 1]) : null;
        const countryName = city.countryId > 0 ? this._decodeTokens(this.countries[city.countryId - 1]) : null;

        let result = cityName;
        if (regionName) {
            result += `, ${regionName}`;
        }
        if (countryName) {
            result += `, ${countryName}`;
        }

        return result;
    }

    /**
     * Get statistics about the loaded database
     */
    getStats() {
        if (!this.isLoaded) {
            return null;
        }

        return {
            cities: this.cities.length,
            regions: this.regions.length,
            countries: this.countries.length,
            vocabularySize: this.vocabulary.size
        };
    }

    /**
     * Find cities by geohash prefix (useful for proximity searches)
     * @param {string} prefix - The geohash prefix to search for
     * @param {number} limit - Maximum number of results (default 50)
     * @returns {Array} - Array of city objects
     */
    findCitiesByGeohashPrefix(prefix, limit = 50) {
        if (!this.isLoaded) {
            throw new Error('Database not loaded');
        }

        const results = [];

        // Find first matching geohash
        let left = 0;
        let right = this.geohashIndex.length - 1;
        let firstMatch = -1;

        while (left <= right) {
            const mid = Math.floor((left + right) / 2);
            const midGeohash = this.geohashIndex[mid].geohash;

            if (midGeohash.startsWith(prefix)) {
                firstMatch = mid;
                right = mid - 1; // Continue searching left for the first match
            } else if (midGeohash < prefix) {
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }

        if (firstMatch === -1) {
            return results;
        }

        // Collect all matching cities
        for (let i = firstMatch; i < this.geohashIndex.length && results.length < limit; i++) {
            const geohash = this.geohashIndex[i].geohash;
            if (!geohash.startsWith(prefix)) {
                break;
            }

            const cityIndex = this.geohashIndex[i].index;
            results.push(this.cities[cityIndex]);
        }

        return results;
    }
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CityDatabase;
} else if (typeof window !== 'undefined') {
    window.CityDatabase = CityDatabase;
}