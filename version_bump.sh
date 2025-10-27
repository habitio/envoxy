#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 [major|minor|patch] [envoxy|envoxyd|both]"
    echo ""
    echo "Arguments:"
    echo "  Bump type: major|minor|patch"
    echo "  Package:   envoxy|envoxyd|both (default: both)"
    echo ""
    echo "Examples:"
    echo "  $0 patch              # Bump patch version for both packages"
    echo "  $0 minor envoxy       # Bump minor version for envoxy only"
    echo "  $0 major both         # Bump major version for both packages"
    exit 1
}

# Check if a parameter is passed
if [ -z "$1" ]; then
    usage
fi

# Determine which packages to update
PACKAGE="${2:-both}"

# Validate package argument
if [[ "$PACKAGE" != "envoxy" && "$PACKAGE" != "envoxyd" && "$PACKAGE" != "both" ]]; then
    echo "Error: Invalid package '$PACKAGE'. Must be 'envoxy', 'envoxyd', or 'both'."
    usage
fi

# Function to bump version in a pyproject.toml file
bump_version() {
    local file=$1
    local bump_type=$2
    local package_name=$3
    
    # Get the current version from pyproject.toml (version = "x.y.z")
    version=$(grep '^version = ' "$file" | awk -F'"' '{print $2}')
    
    # Check if we found a valid version
    if [ -z "$version" ]; then
        echo "Error: Version not found in $file"
        return 1
    fi
    
    # Split the version into major, minor, and patch
    IFS='.' read -r major minor patch <<< "$version"
    
    # Increment the version based on the bump type
    case $bump_type in
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
            echo "Error: Invalid bump type '$bump_type'"
            return 1
            ;;
    esac
    
    # Create the new version string
    new_version="$major.$minor.$patch"
    
    # Update the version in pyproject.toml (cross-platform sed)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i "" "s/^version = \"$version\"/version = \"$new_version\"/" "$file"
    else
        # Linux
        sed -i "s/^version = \"$version\"/version = \"$new_version\"/" "$file"
    fi
    
    echo "✓ $package_name: $version → $new_version"
    return 0
}

# Bump envoxy version
if [[ "$PACKAGE" == "envoxy" || "$PACKAGE" == "both" ]]; then
    if [ -f "pyproject.toml" ]; then
        bump_version "pyproject.toml" "$1" "envoxy"
    else
        echo "Error: pyproject.toml not found"
        exit 1
    fi
fi

# Bump envoxyd version
if [[ "$PACKAGE" == "envoxyd" || "$PACKAGE" == "both" ]]; then
    if [ -f "vendors/pyproject.toml" ]; then
        bump_version "vendors/pyproject.toml" "$1" "envoxyd"
    else
        echo "Error: vendors/pyproject.toml not found"
        exit 1
    fi
fi

echo ""
echo "Version bump complete! Next steps:"
echo "  1. Review changes: git diff pyproject.toml vendors/pyproject.toml"
echo "  2. Commit: git add pyproject.toml vendors/pyproject.toml"
echo "  3. Commit: git commit -m 'chore: Bump version to <new_version>'"
echo "  4. Push to main: git push origin main"
echo "  5. (Optional) Create tag: git tag -a v<new_version> -m 'Release <new_version>'"
