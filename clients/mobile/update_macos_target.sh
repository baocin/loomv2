#!/bin/bash

# Update the macOS deployment target in the Xcode project file
sed -i '' 's/MACOSX_DEPLOYMENT_TARGET = 10.14/MACOSX_DEPLOYMENT_TARGET = 10.15/g' macos/Runner.xcodeproj/project.pbxproj

# Update the macOS deployment target in the Podfile
sed -i '' 's/platform :osx, .*/platform :osx, '\''10.15'\''/g' macos/Podfile

echo "Updated macOS deployment target to 10.15" 