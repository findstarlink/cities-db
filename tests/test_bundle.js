#!/usr/bin/env node
/**
 * Node.js test script for the CityDatabase module
 */

const fs = require('fs');
const path = require('path');

if (process.argv.length < 3) {
    console.error('Usage: node test.js <path_to_city_database>');
    process.exit(1);
}

// Import the CityDatabase class from CLI args
const dbPath = process.argv[2]
const CityDatabase = require('../cityDatabase');

async function runTests() {
    console.log('Testing CityDatabase module in Node.js...\n');

    // Load the bundle file
    if (!fs.existsSync(dbPath)) {
        console.error(`Bundle file not found: ${dbPath}`);
        console.error('Run "python scripts/bundle.py" first to create the bundle.');
        process.exit(1);
    }

    console.log('Loading database bundle...');
    const buffer = fs.readFileSync(dbPath);

    const db = new CityDatabase();
    await db.loadFromBundle(buffer.buffer);

    console.log('Database loaded successfully!\n');

    // Show statistics
    const stats = db.getStats();
    console.log('Database Statistics:');
    console.log(`  Cities: ${stats.cities.toLocaleString()}`);
    console.log(`  Regions: ${stats.regions.toLocaleString()}`);
    console.log(`  Countries: ${stats.countries.toLocaleString()}`);
    console.log(`  Vocabulary: ${stats.vocabularySize.toLocaleString()} tokens\n`);

    // Test specific geohashes
    const testCases = [
        'u14zy',    // 's-Gravenzande
        'u15y0',    // 's-Hertogenbosch  
        's6ruxt',   // 'Ārdamatā
        'stq1d',    // Another city
        'ezdn8',    // Another city
        'nonexistent' // Should return null
    ];

    console.log('Testing specific geohashes:');
    for (const geohash of testCases) {
        const result = db.getCityFromGeohash(geohash);
        if (result) {
            console.log(`  ${geohash}: ${result}`);
        } else {
            console.log(`  ${geohash}: Not found`);
        }
    }

    console.log('\nTesting prefix search for "u1":');
    const prefixResults = db.findCitiesByGeohashPrefix('u1', 5);
    for (const city of prefixResults) {
        const formatted = db.getCityFromGeohash(city.geohash);
        console.log(`  ${city.geohash}: ${formatted}`);
    }

    // Performance test
    console.log('\nPerformance test (1000 random lookups):');
    const startTime = Date.now();
    let found = 0;

    for (let i = 0; i < 1000; i++) {
        // Generate a random geohash-like string
        const randomHash = Math.random().toString(36).substring(2, 8);
        const result = db.getCityFromGeohash(randomHash);
        if (result) found++;
    }

    const endTime = Date.now();
    const duration = endTime - startTime;
    console.log(`  Time: ${duration}ms for 1000 lookups`);
    console.log(`  Average: ${(duration / 1000).toFixed(2)}ms per lookup`);
    console.log(`  Found: ${found} cities out of 1000 random hashes`);

    // Test with actual geohashes for performance
    console.log('\nPerformance test with real geohashes:');
    const realHashes = db.cities.slice(0, 1000).map(city => city.geohash);
    const startTime2 = Date.now();

    for (const hash of realHashes) {
        db.getCityFromGeohash(hash);
    }

    const endTime2 = Date.now();
    const duration2 = endTime2 - startTime2;
    console.log(`  Time: ${duration2}ms for 1000 real geohash lookups`);
    console.log(`  Average: ${(duration2 / 1000).toFixed(3)}ms per lookup`);

    console.log('\n✅ All tests completed successfully!');
}

// Run the tests
runTests().catch(error => {
    console.error('❌ Test failed:', error);
    process.exit(1);
});