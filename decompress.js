// decompresses the compressed cityInfo array

cityInfo.forEach(function (e, i) {
    e[1] = (e[1] ? e[1] : 0);
    e[2] = (e[2] ? e[2] : 0);
    e[3] = (e[3] ? e[3] : 0);
    e[4] = (e[4] ? e[4] : 0);

    e[1] /= 10;
    e[2] /= 10;

    if (i === 0) {
        return;
    }

    var prev = cityInfo[i - 1];
    e[0] += prev[0];
    e[1] += prev[1];
    e[2] += prev[2];
    e[3] += prev[3];
    e[4] += prev[4];
});
