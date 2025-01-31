#!/bin/bash

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is required but not installed. Installing poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install the package in development mode
poetry install

# Create symlink to make mesh-os command available
mkdir -p ~/.local/bin
poetry run pip install --editable .

echo "MeshOS installed successfully!"
echo ""
echo "You can now use the following commands:"
echo "  mesh-os create my-os    # Create a new MeshOS project"
echo "  mesh-os up             # Start services"
echo "  mesh-os down           # Stop services" 