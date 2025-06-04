#!/bin/bash
# Install nuclear-sim globally

echo "Installing Nuclear Plant Simulator..."

# Check if we're in the right directory
if [ ! -f "nuclear-sim" ] || [ ! -f "nuclear_sim.py" ]; then
    echo "Error: Please run this script from the nuclear-simulator directory"
    exit 1
fi

# Create a global installation
INSTALL_DIR="/usr/local/bin"
SCRIPT_DIR="$(pwd)"

# Check if we have write permissions
if [ ! -w "$INSTALL_DIR" ]; then
    echo "Installing to $INSTALL_DIR requires sudo privileges..."
    SUDO="sudo"
else
    SUDO=""
fi

# Create the global script
echo "Creating global nuclear-sim command..."

$SUDO tee "$INSTALL_DIR/nuclear-sim" > /dev/null << EOF
#!/bin/bash
# Nuclear Plant Simulator - Global Installation
# Installed from: $SCRIPT_DIR

# Run the Python CLI from the installation directory
python3 "$SCRIPT_DIR/nuclear_sim.py" "\$@"
EOF

# Make it executable
$SUDO chmod +x "$INSTALL_DIR/nuclear-sim"

echo "✅ Nuclear Plant Simulator installed successfully!"
echo ""
echo "You can now run 'nuclear-sim' from anywhere:"
echo "  nuclear-sim --help"
echo "  nuclear-sim run normal_operation --name 'Test' --duration 300"
echo ""
echo "Installation location: $INSTALL_DIR/nuclear-sim"
echo "Source directory: $SCRIPT_DIR"
