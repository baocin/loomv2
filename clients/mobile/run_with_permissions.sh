#!/bin/bash

echo "Building and running FOOM Sensor App with proper permissions..."

# Clean the project to ensure a fresh build
echo "Cleaning project..."
flutter clean

# Get dependencies
echo "Getting dependencies..."
flutter pub get

# For macOS: Build the app in debug mode
echo "Building app in debug mode..."
flutter build macos --debug

# Create a signed version of the app
echo "Signing the app bundle..."
BUNDLE_PATH=$(find build/macos/Build/Products -name "*.app" -type d | head -n 1)

if [ -z "$BUNDLE_PATH" ]; then
  echo "Error: Could not find built app bundle in build/macos directory"
  exit 1
fi

echo "Found app bundle at: $BUNDLE_PATH"
codesign --force --deep --sign - "$BUNDLE_PATH"

# Run the app
echo "Running the app with proper permissions..."
open "$BUNDLE_PATH"

echo "Done! The app should now be running with proper permissions."
echo "If the app doesn't appear in the macOS Camera permissions, try the following:"
echo "1. Check System Settings > Privacy & Security > Camera"
echo "2. If FOOM Sensor App doesn't appear, restart your Mac and try again"
echo "3. You can also try running the app directly from Finder by navigating to:"
echo "   $BUNDLE_PATH" 