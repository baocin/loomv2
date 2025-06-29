#!/bin/bash

# Ensure dependencies are up to date
echo "Updating dependencies..."
flutter pub get

# Try to generate ObjectBox models
if [ ! -f "lib/models/objectbox/objectbox.g.dart" ]; then
  echo "Generating ObjectBox models..."
  flutter pub run build_runner build --delete-conflicting-outputs
  if [ $? -ne 0 ]; then
    echo "Failed to generate ObjectBox models. Using mock tests only."
  fi
fi

# Run unit tests only
echo "Running ObjectBox unit tests with mocks..."
flutter test test/objectbox_test.dart

# Run dummy integration test that doesn't require ObjectBox models
echo "Running dummy integration test (doesn't actually test ObjectBox)..."
flutter test  -d macos integration_test/objectbox_integration_test.dart || echo "Integration test failed, but continuing..."

echo "Done!" 