#!/bin/bash

echo "==================================================="
echo "Certificate Generator - Setup Script"
echo "==================================================="
echo ""

# Check if Python is installed
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "Python is not installed. Installing Python3..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &>/dev/null; then
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
        else
            echo "Unsupported Linux distribution. Please install Python3 manually."
            exit 1
        fi
        PYTHON_CMD=python3
    else
        echo "Unsupported operating system. Please install Python3 manually."
        exit 1
    fi
fi

# checks python installation
echo ""
echo "Python version:"
$PYTHON_CMD --version


echo ""
echo "---------------------------------------------------"
echo "Creating virtual environment..."
echo "---------------------------------------------------"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo "Virtual environment created successfully."
else
    echo "Virtual environment already exists."
fi

echo ""
echo "---------------------------------------------------"
echo "Activating virtual environment..."
echo "---------------------------------------------------"
source venv/bin/activate

echo ""
echo "---------------------------------------------------"
echo "Upgrading pip..."
echo "---------------------------------------------------"
pip install --upgrade pip

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "---------------------------------------------------"
    echo "Installing system dependencies for PyQt5..."
    echo "---------------------------------------------------"
    
    if command -v apt-get &>/dev/null; then
        # Debian/Ubuntu
        sudo apt-get install -y \
            libxcb-xinerama0 \
            libxcb-icccm4 \
            libxcb-image0 \
            libxcb-keysyms1 \
            libxcb-randr0 \
            libxcb-render-util0 \
            libxcb-shape0 \
            libxkbcommon-x11-0 \
            libgl1-mesa-glx \
            libdbus-1-3 \
            libfontconfig1 \
            libx11-xcb1 \
            2>/dev/null || echo "Some dependencies may already be installed."
    fi
fi

echo ""
echo "---------------------------------------------------"
echo "Installing Python dependencies..."
echo "---------------------------------------------------"

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "Dependencies installed successfully."
else
    echo "Warning: requirements.txt not found. Installing default packages..."
    pip install pandas pillow PyQt5
fi

echo ""
echo "---------------------------------------------------"
echo "Verifying installations..."
echo "---------------------------------------------------"

$PYTHON_CMD -c "import pandas; print('✓ pandas:', pandas.__version__)" 2>/dev/null || echo "✗ pandas installation failed"
$PYTHON_CMD -c "import PIL; print('✓ Pillow:', PIL.__version__)" 2>/dev/null || echo "✗ Pillow installation failed"
$PYTHON_CMD -c "import PyQt5.QtCore; print('✓ PyQt5:', PyQt5.QtCore.PYQT_VERSION_STR)" 2>/dev/null || echo "✗ PyQt5 installation failed"

echo ""
echo "==================================================="
echo "Setup completed successfully!"
echo "==================================================="
echo ""
echo "To run the application, use:"
echo "  ./run.sh"
echo ""

