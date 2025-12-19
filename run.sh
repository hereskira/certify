#!/bin/bash

echo "==================================================="
echo "Certificate Generator - Run Script"
echo "==================================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run setup.sh first:"
    echo "  ./setup.sh"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if certgen_gui.py exists
if [ ! -f "certgen_gui.py" ]; then
    echo "Error: certgen_gui.py not found in current directory."
    exit 1
fi

if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python not found."
    exit 1
fi

# Run the application
echo "Starting Certificate Generator..."
echo ""
$PYTHON_CMD certgen_gui.py

# Deactivate virtual environment on exit
deactivate 2>/dev/null
