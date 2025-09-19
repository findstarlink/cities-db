./make-bundle.sh

# web
cp build/cities_web.js ../web/cities.js

# iOS
iOS_PATH=../app-ios/src/scripts

cp build/countries_ios.ts $iOS_PATH/countries.ts
cp build/cities_ios.ts $iOS_PATH/cities.ts
cp build/admin1_ios.ts $iOS_PATH/admin1.ts
cp build/info_ios.ts $iOS_PATH/info.ts