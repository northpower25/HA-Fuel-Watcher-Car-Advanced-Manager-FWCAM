#!/bin/bash
# Script to delete all pre-releases before v0.1.0
# Usage: ./delete_prereleases.sh [--dry-run]

REPO_OWNER="northpower25"
REPO_NAME="HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM"
DRY_RUN=false

# Check for dry-run flag
if [ "$1" == "--dry-run" ]; then
    DRY_RUN=true
    echo "Running in DRY-RUN mode - no releases will be deleted"
    echo ""
fi

# Pre-release IDs to delete (all releases before v0.1.0)
declare -a PRERELEASE_IDS=(
    "286609357"  # v0.0.110
    "286596521"  # v0.0.109
    "286593561"  # v0.0.108
    "286584664"  # v0.0.107
    "286579575"  # v0.0.106
    "286573540"  # v0.0.105
    "286568023"  # v0.0.104
    "286565209"  # v0.0.103
    "286549245"  # v0.0.102
    "286545944"  # v0.0.101
    "286542677"  # v0.0.100
    "286540307"  # v0.0.99
    "286536662"  # v0.0.98
    "286532453"  # v0.0.97
    "286532099"  # v0.0.96
    "286529267"  # v0.0.95
    "286526860"  # v0.0.94
    "286521817"  # v0.0.93
    "286518202"  # v0.0.92
    "286512585"  # v0.0.91
    "286509900"  # v0.0.90
    "286505528"  # v0.0.89
    "286502750"  # v0.0.88
    "286439846"  # v0.0.87
    "286428784"  # v0.0.86
    "286416742"  # v0.0.85
    "286413507"  # v0.0.84
    "286410011"  # v0.0.83
    "286406417"  # v0.0.82
)

declare -a PRERELEASE_TAGS=(
    "v0.0.110"
    "v0.0.109"
    "v0.0.108"
    "v0.0.107"
    "v0.0.106"
    "v0.0.105"
    "v0.0.104"
    "v0.0.103"
    "v0.0.102"
    "v0.0.101"
    "v0.0.100"
    "v0.0.99"
    "v0.0.98"
    "v0.0.97"
    "v0.0.96"
    "v0.0.95"
    "v0.0.94"
    "v0.0.93"
    "v0.0.92"
    "v0.0.91"
    "v0.0.90"
    "v0.0.89"
    "v0.0.88"
    "v0.0.87"
    "v0.0.86"
    "v0.0.85"
    "v0.0.84"
    "v0.0.83"
    "v0.0.82"
)

echo "Pre-releases to delete: ${#PRERELEASE_IDS[@]}"
echo ""

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI"
    echo "Please run: gh auth login"
    exit 1
fi

# Delete each pre-release
for i in "${!PRERELEASE_IDS[@]}"; do
    RELEASE_ID="${PRERELEASE_IDS[$i]}"
    RELEASE_TAG="${PRERELEASE_TAGS[$i]}"
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would delete: $RELEASE_TAG (ID: $RELEASE_ID)"
    else
        echo "Deleting: $RELEASE_TAG (ID: $RELEASE_ID)"
        if gh release delete "$RELEASE_TAG" --repo "$REPO_OWNER/$REPO_NAME" --yes 2>&1; then
            echo "  ✓ Successfully deleted $RELEASE_TAG"
        else
            echo "  ✗ Failed to delete $RELEASE_TAG"
        fi
    fi
done

echo ""
if [ "$DRY_RUN" = true ]; then
    echo "Dry-run complete. Run without --dry-run to actually delete releases."
else
    echo "Pre-release deletion complete!"
fi
