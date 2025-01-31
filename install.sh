#!/bin/bash

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is required but not installed. Installing poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install the package in development mode
poetry install

# Create symlink to make props-os command available
mkdir -p ~/.local/bin
poetry run pip install --editable .

echo "PropsOS installed successfully!"
echo ""
echo "You can now use the following commands:"
echo "  props-os create my-os    # Create a new PropsOS project"
echo "  props-os up             # Start services"
echo "  props-os down           # Stop services" 