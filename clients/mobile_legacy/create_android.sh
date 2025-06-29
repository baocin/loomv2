#!/bin/bash

echo "Creating Android platform for Loom..."

# Create Android platform
flutter create . --platforms=android --project-name loom --org red.steele

# The above command should create the android directory with the correct package name

echo "Android platform created with package ID: red.steele.loom"
echo ""
echo "You may need to update android/app/build.gradle to set minSdkVersion to 21 or higher"
echo "for some dependencies to work properly."