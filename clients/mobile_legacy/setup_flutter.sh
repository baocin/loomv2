#!/bin/bash

echo "Setting up Flutter project..."

# Clean Flutter project
echo "Cleaning Flutter project..."
flutter clean

# Get dependencies
echo "Getting Flutter dependencies..."
flutter pub get

# Generate ObjectBox code
echo "Generating ObjectBox code..."
flutter pub run build_runner build --delete-conflicting-outputs

echo ""
echo "Setup complete!"
echo ""
echo "To fix the C++ library issue on Linux, you need to install:"
echo "  sudo apt-get install libstdc++-12-dev g++ build-essential"
echo ""
echo "For macOS, the app should work without additional setup."
echo ""
echo "To run the app:"
echo "  flutter run"
echo ""
echo "To run with permissions (macOS):"
echo "  ./run_with_permissions.sh"