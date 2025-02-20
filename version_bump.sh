#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 [major|minor|patch]"
    exit 1
}

# Check if a parameter is passed
if [ -z "$1" ]; then
    usage
fi

# Get the current version from setup.py (version="x.y.z")
version=$(grep 'version=' setup.py | awk -F'"' '{print $2}')

# Check if we found a valid version
if [ -z "$version" ]; then
    echo "Version not found in setup.py. Make sure it's in the format version=\"x.y.z\"."
    exit 1
fi

# Split the version into major, minor, and patch
IFS='.' read -r major minor patch <<< "$version"

# Increment the version based on the input parameter
case $1 in
    major)
        major=$((major + 1))
        minor=0
        patch=0
        ;;
    minor)
        minor=$((minor + 1))
        patch=0
        ;;
    patch)
        patch=$((patch + 1))
        ;;
    *)
        usage
        ;;
esac

# Create the new version string
new_version="$major.$minor.$patch"

# Update the version in setup.py using an alternative delimiter
sed -i "" "s#version=\"$version\"#version=\"$new_version\"#" setup.py

echo "Version updated to $new_version"
