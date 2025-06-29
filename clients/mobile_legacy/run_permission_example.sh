#!/bin/bash

# Check if Flutter is installed
if ! command -v flutter &> /dev/null
then
    echo "Error: Flutter could not be found. Please install Flutter and make sure it's in your PATH."
    exit 1
fi

# Run the permission example app
echo "Running Permission Check Example..."
flutter run -t lib/examples/run_permission_example.dart "$@" 