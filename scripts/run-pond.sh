#!/bin/bash

# Navigate to project root regardless of where this script is called from
cd "$(dirname "$0")/.."

# Default values (can be overridden)
POND_NAME="${POND_NAME:-YourGroupPond}"
GROUP_NAME="${GROUP_NAME:-GroupX}"
BROKER="${BROKER:-localhost}"

# Show usage if --help is passed
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "Fish Haven Pond Runner"
    echo ""
    echo "Usage:"
    echo "  ./scripts/run-pond.sh [--pond-name NAME] [--group-name NAME] [--broker ADDRESS]"
    echo ""
    echo "Or set environment variables:"
    echo "  POND_NAME=MyPond GROUP_NAME=MyGroup ./scripts/run-pond.sh"
    echo ""
    echo "Examples:"
    echo "  ./scripts/run-pond.sh --pond-name BlueLagoon --group-name TeamBlue"
    echo "  POND_NAME=CoralReef ./scripts/run-pond.sh"
    echo ""
    exit 0
fi

# Run the pond application
python pond.py "$@"
